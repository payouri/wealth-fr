"""Data access — load the harmonized dataset into DuckDB and run queries.

DuckDB reads the Parquet output of the pipeline natively, which suits the
filter/group queries behind /api/series and /api/revisions. Falls back to the
cumulative CSV if Parquet is absent.

Holds the four deep, isolation-testable modules of jalon 3: the dataset source
resolver (`_source_relation`), the Ruptures lookup (`ruptures_in`), the Meta
builder (`build_meta`), and the Series resolver (`resolve_series`). `/api/revisions`
(`get_revisions`) is still a stub (jalon 6).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import duckdb

from .models import Meta, Point, Rupture, Series

PARQUET = Path(
    os.environ.get("DATASET_PARQUET", "pipeline/out/dataset_concentration_patrimoine_fr.parquet")
)
CSV = Path(os.environ.get("DATASET_CSV", "pipeline/out/dataset_concentration_patrimoine_fr.csv"))

# Historisation key — identifies one observation across millésimes (CONTEXT.md).
HIST_KEYS = ["annee", "source", "concept_patrimoine", "unite", "groupe", "indicateur"]

# One Unité per Source (the Unité is fixed per Source; the Concept may vary across
# a Rupture). Derived from `source`, echoed back — never required of the caller.
UNITE_BY_SOURCE = {"WID": "adulte", "INSEE": "menage", "DGFiP": "foyer_fiscal"}

# Known methodological breaks, kept in the backend rather than parsed from the
# data's free-form `notes`. Seed: the 2018 ISF→IFI break in DGFiP (CONTEXT.md).
RUPTURES: dict[str, list[tuple[int, str]]] = {
    "DGFiP": [(2018, "ISF (total) → IFI (immobilier)")],
}


def ruptures_in(source: str, annee_min: int, annee_max: int | None) -> list[Rupture]:
    """Ruptures for `source` whose year falls in the requested range.

    Sources with no break (WID, INSEE), or ranges that exclude the break year,
    return `[]` — markers appear only where they are meaningful.
    """
    hi = annee_max if annee_max is not None else 9999
    return [
        Rupture(annee=annee, label=label)
        for annee, label in RUPTURES.get(source, [])
        if annee_min <= annee <= hi
    ]


def _source_relation(con: duckdb.DuckDBPyConnection) -> str:
    """Return a DuckDB-readable reference to the dataset (Parquet preferred)."""
    if PARQUET.exists():
        return f"read_parquet('{PARQUET}')"
    if CSV.exists():
        return f"read_csv_auto('{CSV}')"
    raise FileNotFoundError(
        "No dataset found. Run the pipeline first: "
        "`python pipeline/build_dataset.py` (writes the CSV + Parquet)."
    )


def connect() -> duckdb.DuckDBPyConnection:
    # DuckDB writes its extension cache (`home_directory`) and any query spill
    # (`temp_directory`) to disk, both defaulting to $HOME. The production image
    # runs on a read-only rootfs where only the system temp dir is writable
    # (tmpfs /tmp — see docker-compose.yml), so pin both there. `tempfile.gettempdir()`
    # honours $TMPDIR and falls back to /tmp, so local dev is unaffected.
    scratch = tempfile.gettempdir()
    return duckdb.connect(
        database=":memory:",
        config={"home_directory": scratch, "temp_directory": scratch},
    )


def _distinct(con: duckdb.DuckDBPyConnection, relation: str, column: str) -> list[str]:
    rows = con.execute(f"SELECT DISTINCT {column} FROM {relation} ORDER BY {column}").fetchall()
    return [str(r[0]) for r in rows]


def build_meta(con: duckdb.DuckDBPyConnection, relation: str) -> Meta:
    """Distinct dimension values + global `annee_min`/`annee_max` (HANDOFF §6.4)."""
    bounds = con.execute(f"SELECT min(annee), max(annee) FROM {relation}").fetchone()
    annee_min, annee_max = bounds if bounds else (0, 0)
    return Meta(
        sources=_distinct(con, relation, "source"),
        indicateurs=_distinct(con, relation, "indicateur"),
        groupes=_distinct(con, relation, "groupe"),
        concepts=_distinct(con, relation, "concept_patrimoine"),
        unites=_distinct(con, relation, "unite"),
        millesimes=_distinct(con, relation, "millesime_source"),
        annee_min=int(annee_min),
        annee_max=int(annee_max),
    )


def get_meta() -> Meta:
    con = connect()
    return build_meta(con, _source_relation(con))


class AmbiguousConvention(Exception):
    """The filters still resolve to more than one Convention.

    Carries the available choices so the caller (main.py) can return a 422 that
    prompts the user to pick, rather than silently merging Conventions.
    """

    def __init__(self, choices: list[dict[str, str]]) -> None:
        self.choices = choices
        super().__init__(f"Ambiguous Convention; choose one of {choices}")


def resolve_series(
    con: duckdb.DuckDBPyConnection,
    relation: str,
    *,
    source: str,
    indicateur: str,
    groupe: str,
    concept: str | None = None,
    unite: str | None = None,
    annee_min: int = 2000,
    annee_max: int | None = None,
    euros_constants: bool = False,
    millesime: str | None = None,
) -> Series:
    """Resolve one Convention-pinned, single-Millésime series (ADR 0002).

    (a) derives `unite` from `source`, (b) guards the Convention — raises
    `AmbiguousConvention` if more than one Concept still matches, (c) selects the
    latest `date_extraction` Millésime (or the pinned `millesime`), yielding one
    value per year.
    """
    unite = UNITE_BY_SOURCE.get(source, unite)
    hi = annee_max if annee_max is not None else 9999

    where = "source = ? AND indicateur = ? AND groupe = ? AND annee BETWEEN ? AND ? AND euros_constants = ?"
    params: list[object] = [source, indicateur, groupe, annee_min, hi, euros_constants]
    if unite is not None:
        where += " AND unite = ?"
        params.append(unite)
    if concept is not None:
        where += " AND concept_patrimoine = ?"
        params.append(concept)

    # Guard the Convention: if the matching rows span more than one Concept, the
    # query is ambiguous — never merge or silently pick (CONTEXT.md guard rail).
    concepts = [
        str(r[0])
        for r in con.execute(
            f"SELECT DISTINCT concept_patrimoine FROM {relation} WHERE {where} ORDER BY concept_patrimoine",
            params,
        ).fetchall()
    ]
    if len(concepts) > 1:
        raise AmbiguousConvention(
            [{"unite": unite or "", "concept_patrimoine": c} for c in concepts]
        )

    resolved_concept = concept if concept is not None else (concepts[0] if concepts else "")

    query = {
        "source": source,
        "indicateur": indicateur,
        "groupe": groupe,
        "concept": resolved_concept,
        "unite": unite,
        "annee_min": annee_min,
        "annee_max": annee_max,
        "euros_constants": euros_constants,
        "millesime": millesime,
    }
    ruptures = ruptures_in(source, annee_min, annee_max)

    # Pick the Millésime: the pinned one, else the latest by `date_extraction`.
    if millesime is None:
        row = con.execute(
            f"SELECT millesime_source FROM {relation} WHERE {where} "
            "ORDER BY date_extraction DESC, millesime_source DESC LIMIT 1",
            params,
        ).fetchone()
        millesime = str(row[0]) if row else ""

    point_rows = con.execute(
        f"SELECT annee, valeur FROM {relation} WHERE {where} AND millesime_source = ? "
        "ORDER BY annee",
        [*params, millesime],
    ).fetchall()
    uv_row = con.execute(
        f"SELECT unite_valeur FROM {relation} WHERE {where} AND millesime_source = ? LIMIT 1",
        [*params, millesime],
    ).fetchone()

    return Series(
        query=query,
        unite=unite or "",
        concept_patrimoine=resolved_concept,
        unite_valeur=str(uv_row[0]) if uv_row else "",
        points=[Point(annee=int(a), valeur=float(v)) for a, v in point_rows],
        ruptures=ruptures,
        millesime_source=millesime,
    )


def get_series(**filters) -> Series:
    """Filter by source, indicateur, groupe, concept, unite, annee_min/max,
    euros_constants, millesime. MUST keep unite + concept_patrimoine in the result."""
    con = connect()
    return resolve_series(con, _source_relation(con), **filters)


def get_revisions() -> list[dict]:
    """Observations sharing a HIST_KEYS tuple across >1 millésime_source."""
    raise NotImplementedError
