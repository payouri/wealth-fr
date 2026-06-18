"""Pydantic schemas — the API-facing contract itself (this file and
`frontend/src/api/types.ts` are its two mirrors; keep them in sync).

These mirror the tidy data schema (the `EXPORT_COLUMNS` list in `data.py` and the
pipeline's harmonized output). The two structural dimensions,
`unite` and `concept_patrimoine`, are the Convention and must be preserved and
exposed everywhere (DB -> API -> UI). See CONTEXT.md.

On `/api/series`, `concept` is a required query parameter and `unite` is derived
from `source` (ADR 0002) — these are request-side rules; the response models
below always echo both back.
"""

from __future__ import annotations

from pydantic import BaseModel


class Meta(BaseModel):
    """Lists of available values, to drive first-level UI filters."""

    sources: list[str]
    indicateurs: list[str]
    groupes: list[str]
    concepts: list[str]  # concept_patrimoine
    unites: list[str]
    millesimes: list[str]
    # Per-source `{indicateur: [groupes…]}`: what each Source actually measures.
    # The lists above are a union across sources; this map lets the UI offer a
    # Source only the figures it owns (WID shares vs DGFiP IFI déciles never mix).
    availability: dict[str, dict[str, list[str]]]
    # Per `tranche_marginale_*` groupe, its IFI marginal rate as a number (e.g.
    # {"tranche_marginale_2": 0.7}). Derived from the `(taux marginal X %)` fragment
    # in `notes` (stable per tranche). Lets the UI label a tranche by its rate
    # ("Tranche à 0,7 %") rather than the opaque ordinal — presentation only; the
    # full `groupes`/`availability` lists are unchanged (issue #15).
    tranche_taux: dict[str, float]
    annee_min: int
    annee_max: int


class Point(BaseModel):
    annee: int
    valeur: float


class Rupture(BaseModel):
    """A methodological break to annotate on a series (e.g. 2018 ISF->IFI)."""

    annee: int
    label: str


class Series(BaseModel):
    """Response for GET /api/series — a single filtered series.

    `unite` and `concept_patrimoine` are echoed back because they qualify the
    meaning of every value (the Convention). Never drop them.
    """

    query: dict
    unite: str
    concept_patrimoine: str
    unite_valeur: str
    points: list[Point]
    ruptures: list[Rupture] = []
    millesime_source: str
    date_extraction: str = ""  # traceability: when this millésime was pulled (§3, §7)


class RevisionDiff(BaseModel):
    """An observation that exists in more than one millésime (`/api/revisions`)."""

    annee: int
    source: str
    concept_patrimoine: str
    unite: str
    groupe: str
    indicateur: str
    valeurs: list[dict]  # [{millesime_source, valeur, date_extraction}, ...]


class SourceInfo(BaseModel):
    """Provenance + licence/attribution metadata (data in `data.py` `SOURCE_INFO`, served by `/api/sources`)."""

    source: str
    url: str
    convention: str
    licence: str
    attribution: str


# --- Agent access surface (ADR 0004) -----------------------------------------
# The models below back /api/observations and /api/schema — a programmatic /
# agent-facing surface. They are INTENTIONALLY NOT mirrored into
# `frontend/src/api/types.ts`: the "two mirrors must agree" rule (AGENTS.md)
# governs only the UI contract, and the frontend does not consume these
# endpoints. If a UI surface later consumes them, mirror them then (ADR 0004).


class Observation(BaseModel):
    """One tidy Observation row, returned VERBATIM and self-describing — the
    `EXPORT_COLUMNS` shape (CONTEXT.md tidy schema). Every row carries its own
    Convention (`unite` + `concept_patrimoine`) and traceability (`source`,
    `millesime_source`, `date_extraction`), so co-locating rows from several
    Conventions is never merging (ADR 0004)."""

    annee: int
    source: str
    concept_patrimoine: str
    unite: str
    groupe: str
    indicateur: str
    valeur: float
    unite_valeur: str
    euros_constants: bool
    date_extraction: str
    millesime_source: str
    notes: str | None = None


class ObservationsResponse(BaseModel):
    """Response for GET /api/observations — matching rows co-located, never merged.

    `query` echoes the resolved filters; `total` is the full matched count (so a
    consumer can detect truncation against `limit`); `observations` is the
    `limit`/`offset` page. Never resolves to one Convention and never 422s on
    ambiguity (ADR 0004)."""

    query: dict
    total: int
    limit: int
    offset: int
    observations: list[Observation]


class ConventionGroup(BaseModel):
    """The Conventions one Source carries: its single `unite` and the Concepts it
    spans (one per Concept — e.g. DGFiP `total`/`immobilier` across the 2018
    Rupture). The Convention guard rail forbids comparing across these (CONTEXT.md)."""

    source: str
    unite: str
    concepts: list[str]


class IndicateurSemantics(BaseModel):
    """Per-`indicateur` value semantics: its `unite_valeur` and whether it is
    `dimensionless`. The in-band encoding of ADR 0003 — `%`/`indice` are
    dimensionless (cross-source-comparable in *shape*); `euros*` are levels and
    `effectif` is a count (both NOT dimensionless, never overlaid across Sources)."""

    indicateur: str
    unites_valeur: list[str]
    dimensionless: bool


class SchemaRupture(BaseModel):
    """A known methodological break, with its Source, for /api/schema (e.g. the
    DGFiP 2018 ISF→IFI Rupture). Unlike `Rupture`, it names the Source it belongs
    to so an agent can attribute the break."""

    source: str
    annee: int
    label: str


class Schema(BaseModel):
    """Response for GET /api/schema — the machine-readable contract / agent entry
    point (ADR 0004). Lets an agent learn the Conventions, the per-indicateur
    value semantics with the `dimensionless` flag, the known Ruptures, the
    historisation key, and the guard rails (as English strings) from the API
    itself rather than only from CONTEXT.md out-of-band."""

    conventions: list[ConventionGroup]
    indicateurs: list[IndicateurSemantics]
    ruptures: list[SchemaRupture]
    historisation_key: list[str]
    rules: list[str]
