"""FastAPI app — the API contract from HANDOFF.md §6.4.

`/api/meta` and `/api/series` are implemented (jalon 3); `/api/compare`,
`/api/revisions`, and `/api/sources` remain stubs. Route bodies stay thin and
delegate the §3 / guard-rail logic to `data.py`.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import data
from .models import Meta, RevisionDiff, Series, SourceInfo

app = FastAPI(
    title="Concentration du patrimoine en France",
    description="Explore harmonized wealth-concentration series for France since 2000.",
    version="0.0.1",
)

# Frontend dev server (Vite) origin — tighten for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/meta", response_model=Meta)
def meta():
    return data.get_meta()  # TODO(jalon 3)


@app.get("/api/series", response_model=Series)
def series(
    source: str,
    indicateur: str,
    groupe: str,
    concept: str | None = None,
    unite: str | None = None,
    annee_min: int = 2000,
    annee_max: int | None = None,
    euros_constants: bool = False,
    millesime: str | None = None,
):
    """One Convention-pinned, single-Millésime series (ADR 0002).

    `concept` is part of the required contract (the frontend always sends it);
    the backend additionally guards: if filters still span more than one
    Convention, it returns 422 with the available choices rather than merging.
    """
    try:
        return data.get_series(
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
    except data.AmbiguousConvention as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "ambiguous_convention", "choices": exc.choices},
        ) from exc


@app.get("/api/compare")
def compare(indicateur: str, groupe: str, sources: str):
    """Same indicateur/groupe across several sources. `sources` = CSV list.
    Each returned series keeps its own Convention; never merged. TODO(jalon 5)."""
    raise NotImplementedError


@app.get("/api/revisions", response_model=list[RevisionDiff])
def revisions():
    return data.get_revisions()  # TODO(jalon 6)


@app.get("/api/sources", response_model=list[SourceInfo])
def sources():
    raise NotImplementedError  # TODO(jalon 8): licences/attributions (§7)
