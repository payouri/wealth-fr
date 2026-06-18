"""Pydantic schemas — the API-facing contract and its SINGLE source of truth.

This file is canonical. FastAPI emits these models (plus the route signatures in
`main.py`) as OpenAPI; `frontend/src/api/types.ts` is **generated** from that
OpenAPI by `openapi-typescript` and must never be hand-edited (ADR 0005). The
generation is one-way: change Pydantic here, regenerate (`pnpm gen:contract`), and
CI's `git diff --exit-code` gate fails if the committed artifacts drift.

These mirror the tidy data schema (the `EXPORT_COLUMNS` list in `data.py` and the
pipeline's harmonized output). The two structural dimensions,
`unite` and `concept_patrimoine`, are the Convention and must be preserved and
exposed everywhere (DB -> API -> UI). See CONTEXT.md.

Vocabulary is split (ADR 0005): `Source` / `Unite` / `Indicateur` are **closed**
`Literal`s used in both the models and the route params (so they become OpenAPI
enums and FastAPI 422s an unknown value for free), while `concept_patrimoine` and
`groupe` stay **open** `str`s, discovered at runtime via `/api/meta`. A new concept
(e.g. INSEE `brut_hors_reste`) appears with no code change here.

On `/api/series`, `concept` is a required query parameter and `unite` is derived
from `source` (ADR 0002) — these are request-side rules; the response models
below always echo both back.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# --- Closed vocabulary (ADR 0005) --------------------------------------------
# These three axes are CURATED, not raw data granularity, so they are closed
# `Literal`s shared by the Pydantic models AND the FastAPI route params. Closing
# them emits OpenAPI enums (-> generated TS unions) and makes FastAPI reject an
# unknown value with 422 for free. `concept_patrimoine` / `groupe` are NOT here:
# they stay open strings, discovered via /api/meta. Adding a value below is a
# deliberate schema change (regenerate types.ts), not a doc edit.

# The three public sources whose Conventions are not interchangeable (CONTEXT.md).
Source = Literal["WID", "INSEE", "DGFiP"]

# One Unité per Source (the population unit half of the Convention).
Unite = Literal["adulte", "menage", "foyer_fiscal"]

# The curated set of measures. Adding a 7th is an intentional schema change.
Indicateur = Literal[
    "part_patrimoine",
    "gini",
    "patrimoine_moyen",
    "seuil",
    "nb_foyers",
    "impot_moyen",
]


class Meta(BaseModel):
    """Lists of available values, to drive first-level UI filters."""

    sources: list[Source]
    indicateurs: list[Indicateur]
    groupes: list[str]
    concepts: list[str]  # concept_patrimoine — open vocabulary (ADR 0005)
    unites: list[Unite]
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
    unite: Unite
    concept_patrimoine: str  # open vocabulary (ADR 0005)
    unite_valeur: str
    points: list[Point]
    ruptures: list[Rupture] = []
    millesime_source: str
    date_extraction: str = ""  # traceability: when this millésime was pulled (§3, §7)


class ConventionChoice(BaseModel):
    """One Convention the caller may pin to resolve a 422 (ADR 0002). `unite` is
    closed; `concept_patrimoine` stays an OPEN string (ADR 0005)."""

    unite: str
    concept_patrimoine: str


class AmbiguousConventionDetail(BaseModel):
    """The `422` body when filters still span more than one Convention (ADR 0002).

    Wraps the choices the caller can pin. `error` is a closed literal so the
    frontend can branch on it. The `@app.exception_handler` in `main.py` produces
    this body at runtime under a `{"detail": …}` envelope; declaring the model via
    `responses={422: {"model": AmbiguousConventionDetail}}` only makes it visible
    to OpenAPI (and thus generated for the frontend)."""

    error: Literal["ambiguous_convention"] = "ambiguous_convention"
    choices: list[ConventionChoice]


class RevisionValeur(BaseModel):
    """One competing Millésime of a revised Observation: its value and the
    `date_extraction` that orders the révision (append-only historisation)."""

    millesime_source: str
    valeur: float
    date_extraction: str


class RevisionDiff(BaseModel):
    """An observation that exists in more than one millésime (`/api/revisions`)."""

    annee: int
    source: Source
    concept_patrimoine: str
    unite: Unite
    groupe: str
    indicateur: Indicateur
    valeurs: list[RevisionValeur]


class SourceInfo(BaseModel):
    """Provenance + licence/attribution metadata (data in `data.py` `SOURCE_INFO`, served by `/api/sources`)."""

    source: Source
    url: str
    convention: str
    licence: str
    attribution: str


# --- Agent access surface (ADR 0004) -----------------------------------------
# The models below back /api/observations and /api/schema — a programmatic /
# agent-facing surface. Under backend-canonical codegen (ADR 0005) they DO appear
# in the generated `frontend/src/api/types.ts` (it is emitted from the OpenAPI
# schema, which includes them); that is expected and harmless. The point that the
# FRONTEND does not consume these endpoints still stands — they exist for agents.


class Observation(BaseModel):
    """One tidy Observation row, returned VERBATIM and self-describing — the
    `EXPORT_COLUMNS` shape (CONTEXT.md tidy schema). Every row carries its own
    Convention (`unite` + `concept_patrimoine`) and traceability (`source`,
    `millesime_source`, `date_extraction`), so co-locating rows from several
    Conventions is never merging (ADR 0004)."""

    annee: int
    source: Source
    concept_patrimoine: str
    unite: Unite
    groupe: str
    indicateur: Indicateur
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

    source: Source
    unite: Unite
    concepts: list[str]


class IndicateurSemantics(BaseModel):
    """Per-`indicateur` value semantics: its `unite_valeur` and whether it is
    `dimensionless`. The in-band encoding of ADR 0003 — `%`/`indice` are
    dimensionless (cross-source-comparable in *shape*); `euros*` are levels and
    `effectif` is a count (both NOT dimensionless, never overlaid across Sources)."""

    indicateur: Indicateur
    unites_valeur: list[str]
    dimensionless: bool


class SchemaRupture(BaseModel):
    """A known methodological break, with its Source, for /api/schema (e.g. the
    DGFiP 2018 ISF→IFI Rupture). Unlike `Rupture`, it names the Source it belongs
    to so an agent can attribute the break."""

    source: Source
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
