"""Data access — load the harmonized dataset into DuckDB and run queries.

DuckDB reads the Parquet output of the pipeline natively, which suits the
filter/group queries behind /api/series and /api/revisions. Falls back to the
cumulative CSV if Parquet is absent.

Holds the deep, isolation-testable modules: the dataset source resolver
(`_source_relation`), the Ruptures lookup (`ruptures_in`), the Meta builder
(`build_meta`), and the query resolver (`_resolve_query`) shared by the Series
view (`resolve_series`), the cross-source comparison (`resolve_compare`, jalon 5)
and the tidy-rows export (`resolve_rows`, jalon 9). Révisions (`resolve_revisions`,
jalon 6) and the static Source metadata (`SOURCE_INFO`, jalon 8) live here too.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import NamedTuple

import duckdb

from .models import (
    ConventionGroup,
    IndicateurSemantics,
    Meta,
    Point,
    RevisionDiff,
    Rupture,
    Schema,
    SchemaRupture,
    Series,
    SourceInfo,
)

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


def _availability(con: duckdb.DuckDBPyConnection, relation: str) -> dict[str, dict[str, list[str]]]:
    """Per-source `{indicateur: [groupes…]}` map of what each Source actually
    measures. The global `indicateurs`/`groupes` lists are a union across sources
    — but the Sources measure disjoint things (WID shares vs DGFiP IFI déciles),
    so the UI must only offer a Source the indicateurs/groupes it owns. Driving
    the filters off this map keeps the reader from asking a Source for a figure it
    never measured (Convention guard rail; CONTEXT.md)."""
    rows = con.execute(
        f"SELECT DISTINCT source, indicateur, groupe FROM {relation} "
        "ORDER BY source, indicateur, groupe"
    ).fetchall()
    out: dict[str, dict[str, list[str]]] = {}
    for source, indicateur, groupe in rows:
        out.setdefault(str(source), {}).setdefault(str(indicateur), []).append(str(groupe))
    return out


_TRANCHE_TAUX_RE = re.compile(r"taux marginal\s+([\d]+(?:[.,]\d+)?)\s*%")


def _tranche_taux(con: duckdb.DuckDBPyConnection, relation: str) -> dict[str, float]:
    """Map each `tranche_marginale_*` groupe to its IFI marginal rate, read from the
    `(taux marginal X %)` fragment in `notes`. The rate is a stable data fact per
    tranche (same across years), so a tranche is labelled by its rate rather than
    its opaque ordinal (which starts at 2 and skips the 0,5 % band; CONTEXT.md,
    issue #15). A tranche whose notes carry no parseable rate is simply omitted."""
    rows = con.execute(
        f"SELECT DISTINCT groupe, notes FROM {relation} WHERE groupe LIKE 'tranche_marginale_%' "
        "ORDER BY groupe, notes"
    ).fetchall()
    out: dict[str, float] = {}
    for groupe, notes in rows:
        if notes is None or groupe in out:
            continue
        m = _TRANCHE_TAUX_RE.search(str(notes))
        if m:
            out[str(groupe)] = float(m.group(1).replace(",", "."))
    return out


def build_meta(con: duckdb.DuckDBPyConnection, relation: str) -> Meta:
    """Distinct dimension values + global `annee_min`/`annee_max` (serves `/api/meta`)."""
    bounds = con.execute(f"SELECT min(annee), max(annee) FROM {relation}").fetchone()
    annee_min, annee_max = bounds if bounds else (0, 0)
    return Meta(
        sources=_distinct(con, relation, "source"),
        indicateurs=_distinct(con, relation, "indicateur"),
        groupes=_distinct(con, relation, "groupe"),
        concepts=_distinct(con, relation, "concept_patrimoine"),
        unites=_distinct(con, relation, "unite"),
        millesimes=_distinct(con, relation, "millesime_source"),
        availability=_availability(con, relation),
        tranche_taux=_tranche_taux(con, relation),
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


# Tidy schema columns, in order — the export surface and the canonical row shape
# (mirrors the pipeline's harmonized output + `models.py`). Kept here so a single
# list defines what /api/export.csv streams.
EXPORT_COLUMNS = [
    "annee",
    "source",
    "concept_patrimoine",
    "unite",
    "groupe",
    "indicateur",
    "valeur",
    "unite_valeur",
    "euros_constants",
    "date_extraction",
    "millesime_source",
    "notes",
]


class _Resolved(NamedTuple):
    """The outcome of resolving a query: the Convention-pinned, single-Millésime
    selection shared by `resolve_series` (points view) and `resolve_rows` (tidy
    rows view), so the guard-rail logic lives in exactly one place."""

    where: str
    params: list[object]
    unite: str | None
    concept: str
    millesime: str
    ruptures: list[Rupture]


def _resolve_query(
    con: duckdb.DuckDBPyConnection,
    relation: str,
    *,
    source: str,
    indicateur: str,
    groupe: str,
    concept: str | None,
    unite: str | None,
    annee_min: int,
    annee_max: int | None,
    euros_constants: bool,
    millesime: str | None,
) -> _Resolved:
    """(a) derive `unite` from `source`, (b) guard the Convention (raise
    `AmbiguousConvention` if >1 Concept still matches), (c) pick the Millésime
    (pinned, else latest by `date_extraction`). The one resolution path (ADR 0002)."""
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

    # Pick the Millésime: the pinned one, else the latest by `date_extraction`.
    if millesime is None:
        row = con.execute(
            f"SELECT millesime_source FROM {relation} WHERE {where} "
            "ORDER BY date_extraction DESC, millesime_source DESC LIMIT 1",
            params,
        ).fetchone()
        millesime = str(row[0]) if row else ""

    return _Resolved(
        where=where,
        params=params,
        unite=unite,
        concept=resolved_concept,
        millesime=millesime,
        ruptures=ruptures_in(source, annee_min, annee_max),
    )


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

    Delegates the Convention guard and Millésime pick to `_resolve_query`, then
    projects the selection to one value per year.
    """
    r = _resolve_query(
        con,
        relation,
        source=source,
        indicateur=indicateur,
        groupe=groupe,
        concept=concept,
        unite=unite,
        annee_min=annee_min,
        annee_max=annee_max,
        euros_constants=euros_constants,
        millesime=millesime,
    )
    where, params, unite, resolved_concept, millesime = (
        r.where,
        r.params,
        r.unite,
        r.concept,
        r.millesime,
    )

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
    ruptures = r.ruptures

    point_rows = con.execute(
        f"SELECT annee, valeur FROM {relation} WHERE {where} AND millesime_source = ? "
        "ORDER BY annee",
        [*params, millesime],
    ).fetchall()
    uv_row = con.execute(
        f"SELECT unite_valeur, max(date_extraction) FROM {relation} "
        f"WHERE {where} AND millesime_source = ? GROUP BY unite_valeur LIMIT 1",
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
        date_extraction=str(uv_row[1]) if uv_row and uv_row[1] is not None else "",
    )


def get_series(**filters) -> Series:
    """Filter by source, indicateur, groupe, concept, unite, annee_min/max,
    euros_constants, millesime. MUST keep unite + concept_patrimoine in the result."""
    con = connect()
    return resolve_series(con, _source_relation(con), **filters)


def resolve_rows(
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
) -> list[dict]:
    """The tidy rows the resolver selects (jalon 9 export), not a points view.

    Shares `_resolve_query` with `resolve_series` — same Convention guard, same
    single-Millésime pick — and projects the full tidy schema (`EXPORT_COLUMNS`),
    so the exported CSV is exactly what the chart was drawn from, Convention and
    all.
    """
    r = _resolve_query(
        con,
        relation,
        source=source,
        indicateur=indicateur,
        groupe=groupe,
        concept=concept,
        unite=unite,
        annee_min=annee_min,
        annee_max=annee_max,
        euros_constants=euros_constants,
        millesime=millesime,
    )
    cols = ", ".join(EXPORT_COLUMNS)
    rows = con.execute(
        f"SELECT {cols} FROM {relation} WHERE {r.where} AND millesime_source = ? ORDER BY annee",
        [*r.params, r.millesime],
    ).fetchall()
    return [dict(zip(EXPORT_COLUMNS, row, strict=True)) for row in rows]


def get_export_rows(**filters) -> list[dict]:
    con = connect()
    return resolve_rows(con, _source_relation(con), **filters)


def _in_clause(
    column: str, values: list[str] | None, where: list[str], params: list[object]
) -> None:
    """Append an optional multi-value (comma-list) filter as a SQL `IN (…)` — the
    union of the given values, or no constraint when `values` is falsy. The agent
    surface's filters are all optional and select the union (ADR 0004)."""
    if values:
        placeholders = ", ".join("?" for _ in values)
        where.append(f"{column} IN ({placeholders})")
        params.extend(values)


def resolve_observations(
    con: duckdb.DuckDBPyConnection,
    relation: str,
    *,
    source: list[str] | None = None,
    indicateur: list[str] | None = None,
    groupe: list[str] | None = None,
    concept: list[str] | None = None,
    unite: list[str] | None = None,
    millesime: list[str] | None = None,
    annee_min: int = 2000,
    annee_max: int | None = None,
    euros_constants: bool | None = None,
    limit: int = 5000,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """The matching tidy Observation rows VERBATIM, plus the full matched `total`.

    The faithful, unpinned agent read behind /api/observations (ADR 0004).
    Deliberately does NOT call `_resolve_query` and NEVER raises
    `AmbiguousConvention`: co-locating self-describing rows across several
    Conventions is not merging — every row still carries its own `unite`,
    `concept_patrimoine`, `millesime_source` and `date_extraction`. All matching
    Millésimes are returned (Révisions visible inline, never deduped); both
    nominal and `euros_constants` rows are returned unless narrowed. Filters are
    optional multi-value comma-lists selecting the union; an omitted filter is
    unconstrained. `total` is the full matched count (for truncation detection)
    while `limit`/`offset` slice the returned page.
    """
    hi = annee_max if annee_max is not None else 9999
    where: list[str] = ["annee BETWEEN ? AND ?"]
    params: list[object] = [annee_min, hi]
    _in_clause("source", source, where, params)
    _in_clause("indicateur", indicateur, where, params)
    _in_clause("groupe", groupe, where, params)
    _in_clause("concept_patrimoine", concept, where, params)
    _in_clause("unite", unite, where, params)
    _in_clause("millesime_source", millesime, where, params)
    if euros_constants is not None:
        where.append("euros_constants = ?")
        params.append(euros_constants)

    clause = " AND ".join(where)
    total_row = con.execute(f"SELECT count(*) FROM {relation} WHERE {clause}", params).fetchone()
    total = int(total_row[0]) if total_row else 0

    # Project `date_extraction` as text: DuckDB infers it as a DATE, but the tidy
    # contract (and the Observation model) carries it as the raw extraction-date
    # string — same posture as resolve_series/resolve_revisions, which str() it.
    cols = ", ".join(
        f"CAST({c} AS VARCHAR) AS {c}" if c == "date_extraction" else c for c in EXPORT_COLUMNS
    )
    rows = con.execute(
        f"SELECT {cols} FROM {relation} WHERE {clause} "
        f"ORDER BY {', '.join(HIST_KEYS)}, millesime_source, date_extraction "
        "LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    return [dict(zip(EXPORT_COLUMNS, row, strict=True)) for row in rows], total


def get_observations(**filters) -> tuple[list[dict], int]:
    con = connect()
    return resolve_observations(con, _source_relation(con), **filters)


# `unite_valeur` values that are dimensionless — shares (%) and the Gini indice.
# These are cross-source-comparable in *shape* (ADR 0003); everything else
# (`euros`, `euros_constants_2021` = levels; `effectif`-style counts) is bound to
# its Convention and must never be overlaid across Sources.
_DIMENSIONLESS_UNITES_VALEUR = {"%", "indice"}


def _is_dimensionless(unites_valeur: list[str]) -> bool:
    """An indicateur is dimensionless only if EVERY `unite_valeur` it carries is
    dimensionless (the in-band encoding of ADR 0003). A levels/count `unite_valeur`
    disqualifies it — it is Convention-bound, not overlay-safe across Sources."""
    return bool(unites_valeur) and all(uv in _DIMENSIONLESS_UNITES_VALEUR for uv in unites_valeur)


# The guard rails as machine-readable English, sourced from the CONTEXT.md
# non-negotiables (AGENTS.md). Published in /api/schema so an agent can self-police
# rather than learn them out-of-band (ADR 0004).
GUARD_RAIL_RULES = [
    "Never aggregate or compare values across Conventions: a Convention is an "
    "(unite + concept_patrimoine) pair, and values are only comparable within the "
    "same Convention. Co-locating self-describing rows from several Conventions is "
    "fine; merging them into one series is not.",
    "euros_constants (deflated levels) apply only to levels — never deflate shares "
    "(%) or Gini. A euros_constants_2021 row is added alongside the nominal one, "
    "never replacing it.",
    "Historisation is append-only: when a Source revises a past value, both "
    "Millésimes coexist (a Révision). Observations are never overwritten; all "
    "matching Millésimes are returned, labelled by millesime_source.",
    "Traceability is a feature: source, millesime_source and date_extraction stay "
    "visible for every displayed figure.",
]


def build_schema(con: duckdb.DuckDBPyConnection, relation: str) -> Schema:
    """The machine-readable contract / agent entry point behind /api/schema (ADR
    0004): the Conventions (distinct source → unite → concepts), the per-indicateur
    value semantics with the `dimensionless` flag (in-band ADR 0003), the known
    Ruptures (from `RUPTURES`), the historisation key (`HIST_KEYS`), and the guard
    rails as English strings. Read-only; derived from the dataset + backend tables."""
    conv_rows = con.execute(
        f"SELECT DISTINCT source, unite, concept_patrimoine FROM {relation} "
        "ORDER BY source, unite, concept_patrimoine"
    ).fetchall()
    grouped: dict[tuple[str, str], list[str]] = {}
    for source, unite, concept in conv_rows:
        grouped.setdefault((str(source), str(unite)), []).append(str(concept))
    conventions = [
        ConventionGroup(source=source, unite=unite, concepts=concepts)
        for (source, unite), concepts in grouped.items()
    ]

    ind_rows = con.execute(
        f"SELECT DISTINCT indicateur, unite_valeur FROM {relation} "
        "ORDER BY indicateur, unite_valeur"
    ).fetchall()
    by_indicateur: dict[str, list[str]] = {}
    for indicateur, unite_valeur in ind_rows:
        by_indicateur.setdefault(str(indicateur), []).append(str(unite_valeur))
    indicateurs = [
        IndicateurSemantics(
            indicateur=indicateur,
            unites_valeur=unites_valeur,
            dimensionless=_is_dimensionless(unites_valeur),
        )
        for indicateur, unites_valeur in by_indicateur.items()
    ]

    ruptures = [
        SchemaRupture(source=source, annee=annee, label=label)
        for source, breaks in RUPTURES.items()
        for annee, label in breaks
    ]

    return Schema(
        conventions=conventions,
        indicateurs=indicateurs,
        ruptures=ruptures,
        historisation_key=list(HIST_KEYS),
        rules=list(GUARD_RAIL_RULES),
    )


def get_schema() -> Schema:
    con = connect()
    return build_schema(con, _source_relation(con))


def resolve_revisions(con: duckdb.DuckDBPyConnection, relation: str) -> list[RevisionDiff]:
    """Observations the source revised: same HIST_KEYS tuple, >1 millésime, and a
    value that actually changed (append-only historisation; CONTEXT.md).

    A tuple present in several millésimes with an *unchanged* value is not a
    Révision — nothing was revised — so it is filtered out (the diff table is
    "where did the source change a past number", not "which rows were re-pulled").
    Both competing millésimes are kept, each with its own value and
    `date_extraction`; neither is ever overwritten.
    """
    keys = ", ".join(HIST_KEYS)
    rows = con.execute(
        f"SELECT {keys}, millesime_source, valeur, date_extraction FROM {relation} "
        f"WHERE ({keys}) IN ("
        f"  SELECT {keys} FROM {relation} GROUP BY {keys} "
        "   HAVING count(DISTINCT millesime_source) > 1 AND count(DISTINCT valeur) > 1"
        f") ORDER BY {keys}, date_extraction"
    ).fetchall()

    out: dict[tuple, RevisionDiff] = {}
    for r in rows:
        annee, source, concept, unite, groupe, indicateur = r[:6]
        millesime, valeur, date_extraction = r[6], r[7], r[8]
        key = (int(annee), source, concept, unite, groupe, indicateur)
        diff = out.get(key)
        if diff is None:
            diff = RevisionDiff(
                annee=int(annee),
                source=str(source),
                concept_patrimoine=str(concept),
                unite=str(unite),
                groupe=str(groupe),
                indicateur=str(indicateur),
                valeurs=[],
            )
            out[key] = diff
        diff.valeurs.append(
            {
                "millesime_source": str(millesime),
                "valeur": float(valeur),
                "date_extraction": str(date_extraction) if date_extraction is not None else "",
            }
        )
    return list(out.values())


# Provenance + licence/attribution per Source — the source of truth, served by
# /api/sources. Static metadata — the methodology page renders it so reuse terms
# stay in sync with the data.
SOURCE_INFO: list[SourceInfo] = [
    SourceInfo(
        source="WID",
        url="https://wid.world",
        convention="adultes · patrimoine net",
        licence="Citation requise (vérifier les conditions de réutilisation en vigueur)",
        attribution="WID.world — Garbinti, Goupille-Lebret, Piketty",
    ),
    SourceInfo(
        source="INSEE",
        url="https://www.insee.fr",
        convention="ménages · brut/net (et hors reste)",
        licence="Licence Ouverte / Open Licence (Etalab) — à vérifier par jeu de données",
        attribution="INSEE — enquêtes Patrimoine / Histoire de vie et patrimoine (HVP, API Melodi)",
    ),
    SourceInfo(
        source="DGFiP",
        url="https://www.impots.gouv.fr",
        convention="foyers fiscaux · ISF (≤2017) / IFI (≥2018)",
        licence="Licence Ouverte / Open Licence (Etalab) — data.gouv.fr",
        attribution="DGFiP — Statistiques ISF/IFI (impots.gouv.fr, data.gouv.fr)",
    ),
]


def get_sources() -> list[SourceInfo]:
    return SOURCE_INFO


def resolve_compare(
    con: duckdb.DuckDBPyConnection,
    relation: str,
    *,
    indicateur: str,
    groupe: str,
    sources: list[str],
) -> list[Series]:
    """One Series per Source for the same indicateur/groupe (jalon 5, ADR 0003).

    Each Source goes through `resolve_series`, so its Convention is auto-derived
    and preserved — Sources are overlaid, never merged. Any Source still spanning
    more than one Convention raises `AmbiguousConvention`, surfacing the same 422
    contract as `/api/series`; no parallel resolution logic.
    """
    return [
        resolve_series(con, relation, source=source, indicateur=indicateur, groupe=groupe)
        for source in sources
    ]


def get_compare(indicateur: str, groupe: str, sources: list[str]) -> list[Series]:
    con = connect()
    return resolve_compare(
        con, _source_relation(con), indicateur=indicateur, groupe=groupe, sources=sources
    )


def get_revisions() -> list[RevisionDiff]:
    """Observations sharing a HIST_KEYS tuple across >1 millésime_source."""
    con = connect()
    return resolve_revisions(con, _source_relation(con))
