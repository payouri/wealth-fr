"""FastAPI app — the API contract from HANDOFF.md §6.4.

All read endpoints are implemented: `/api/meta` + `/api/series` (jalon 3),
`/api/compare` (jalon 5), `/api/revisions` (jalon 6), `/api/sources` (jalon 8)
and `/api/export.csv` (jalon 9). Route bodies stay thin and delegate the §3 /
guard-rail logic to `data.py`; the new endpoints reuse the jalon-3 resolver.
"""

from __future__ import annotations

import csv
import io
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

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


@app.get("/api/compare", response_model=list[Series])
def compare(indicateur: str, groupe: str, sources: str):
    """Same indicateur/groupe across several sources. `sources` = CSV list.

    Each returned series keeps its own Convention; never merged (jalon 5, ADR
    0003). A source still spanning more than one Convention surfaces the same
    422 "pick a Convention" contract as /api/series.
    """
    source_list = [s.strip() for s in sources.split(",") if s.strip()]
    try:
        return data.get_compare(indicateur=indicateur, groupe=groupe, sources=source_list)
    except data.AmbiguousConvention as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "ambiguous_convention", "choices": exc.choices},
        ) from exc


@app.get("/api/revisions", response_model=list[RevisionDiff])
def revisions():
    return data.get_revisions()  # TODO(jalon 6)


@app.get("/api/sources", response_model=list[SourceInfo])
def sources():
    """Provenance + licence/attribution per Source (jalon 8, HANDOFF §7)."""
    return data.get_sources()


@app.get("/api/export.csv")
def export_csv(
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
    """Stream the resolved tidy rows as CSV (jalon 9).

    Reuses the jalon-3 resolver (`resolve_rows`), so the export is exactly the
    rows the chart was drawn from — same Convention guard, same single-Millésime
    pick, same 422 "pick a Convention" contract.
    """
    try:
        rows = data.get_export_rows(
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

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=data.EXPORT_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    # Sanitize the filter parts before they land in the Content-Disposition
    # header: a quote (or other odd char) in a query param would break the
    # quoted filename. Mirrors the frontend's `exportStem` so server- and
    # client-named downloads agree.
    stem = re.sub(r"[^\w.-]+", "-", f"{source}_{indicateur}_{groupe}")
    filename = f"{stem}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
