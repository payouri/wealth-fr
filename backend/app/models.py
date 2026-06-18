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
