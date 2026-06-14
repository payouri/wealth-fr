"""Pydantic schemas — the API-facing contract (HANDOFF.md §6.4).

These mirror the tidy data schema (HANDOFF.md §3). The two structural dimensions,
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


class RevisionDiff(BaseModel):
    """An observation that exists in more than one millésime (HANDOFF.md §6.4)."""

    annee: int
    source: str
    concept_patrimoine: str
    unite: str
    groupe: str
    indicateur: str
    valeurs: list[dict]  # [{millesime_source, valeur, date_extraction}, ...]


class SourceInfo(BaseModel):
    """Provenance + licence/attribution metadata (HANDOFF.md §7)."""

    source: str
    url: str
    convention: str
    licence: str
    attribution: str
