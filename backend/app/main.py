"""FastAPI app — the API contract (these route signatures + the Pydantic models
in `models.py`). FastAPI emits this as OpenAPI; `frontend/src/api/types.ts` is
**generated** from that schema and never hand-edited (ADR 0005). The closed axes
`source` / `indicateur` / `unite` are typed with the `models.py` Literals here too,
so they become OpenAPI enums (FastAPI 422s an unknown value for free); `concept`
and `groupe` stay open strings, discovered via /api/meta.

All read endpoints are implemented: `/api/meta` + `/api/series` (jalon 3),
`/api/compare` (jalon 5), `/api/revisions` (jalon 6), `/api/sources` (jalon 8)
and `/api/export.csv` (jalon 9). Route bodies stay thin and delegate the
schema / guard-rail logic to `data.py`; the new endpoints reuse the jalon-3 resolver.
"""

from __future__ import annotations

import csv
import io
import re

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from . import data
from .models import (
    AmbiguousConventionDetail,
    Indicateur,
    Meta,
    Observation,
    ObservationsResponse,
    RevisionDiff,
    Schema,
    Series,
    Source,
    SourceInfo,
    Unite,
)

# The 422 "pick a Convention" body, declared on every route that resolves a
# single Convention (series, compare, export.csv). The body itself is still
# produced at runtime by `_ambiguous_convention` below; this only surfaces the
# shape to OpenAPI so it is generated for the frontend (ADR 0005).
_AMBIGUOUS_CONVENTION_RESPONSES: dict = {422: {"model": AmbiguousConventionDetail}}

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


@app.exception_handler(data.AmbiguousConvention)
async def _ambiguous_convention(_: Request, exc: Exception) -> JSONResponse:
    """Map the Convention guard rail to one 422 "pick a Convention" for every
    endpoint that resolves a query (series, compare, export.csv) — never merge
    Conventions silently. Keeps the body shape the frontend's ApiError reads
    (`detail.error` / `detail.choices`)."""
    assert isinstance(exc, data.AmbiguousConvention)
    return JSONResponse(
        status_code=422,
        content={"detail": {"error": "ambiguous_convention", "choices": exc.choices}},
    )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/meta", response_model=Meta)
def meta():
    return data.get_meta()  # TODO(jalon 3)


@app.get("/api/series", response_model=Series, responses=_AMBIGUOUS_CONVENTION_RESPONSES)
def series(
    source: Source,
    indicateur: Indicateur,
    groupe: str,
    concept: str | None = None,
    unite: Unite | None = None,
    annee_min: int = 2000,
    annee_max: int | None = None,
    euros_constants: bool = False,
    millesime: str | None = None,
):
    """One Convention-pinned, single-Millésime series (ADR 0002).

    `concept` is part of the required contract (the frontend always sends it);
    the backend additionally guards: if filters still span more than one
    Convention, it returns 422 with the available choices rather than merging
    (handled centrally by `_ambiguous_convention`).
    """
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


@app.get("/api/compare", response_model=list[Series], responses=_AMBIGUOUS_CONVENTION_RESPONSES)
def compare(indicateur: Indicateur, groupe: str, sources: str):
    """Same indicateur/groupe across several sources. `sources` = CSV list.

    Each returned series keeps its own Convention; never merged (jalon 5, ADR
    0003). A source still spanning more than one Convention surfaces the same
    422 "pick a Convention" contract as /api/series.
    """
    source_list = [s.strip() for s in sources.split(",") if s.strip()]
    return data.get_compare(indicateur=indicateur, groupe=groupe, sources=source_list)


@app.get("/api/revisions", response_model=list[RevisionDiff])
def revisions():
    return data.get_revisions()  # TODO(jalon 6)


@app.get("/api/sources", response_model=list[SourceInfo])
def sources():
    """Provenance + licence/attribution per Source (jalon 8; data in `data.py` `SOURCE_INFO`)."""
    return data.get_sources()


@app.get("/api/export.csv", responses=_AMBIGUOUS_CONVENTION_RESPONSES)
def export_csv(
    source: Source,
    indicateur: Indicateur,
    groupe: str,
    concept: str | None = None,
    unite: Unite | None = None,
    annee_min: int = 2000,
    annee_max: int | None = None,
    euros_constants: bool = False,
    millesime: str | None = None,
):
    """Stream the resolved tidy rows as CSV (jalon 9).

    Reuses the jalon-3 resolver (`resolve_rows`), so the export is exactly the
    rows the chart was drawn from — same Convention guard, same single-Millésime
    pick, same 422 "pick a Convention" contract (handled centrally).
    """
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


def _csv_list(value: str | None) -> list[str] | None:
    """Parse an optional comma-separated query param into a list (the union of
    values), or `None` when omitted/empty — an omitted filter is unconstrained
    (ADR 0004)."""
    if value is None:
        return None
    items = [v.strip() for v in value.split(",") if v.strip()]
    return items or None


@app.get("/api/observations", response_model=ObservationsResponse)
def observations(
    source: str | None = None,
    indicateur: str | None = None,
    groupe: str | None = None,
    concept: str | None = None,
    unite: str | None = None,
    millesime: str | None = None,
    annee_min: int = 2000,
    annee_max: int | None = None,
    euros_constants: bool | None = None,
    # Paging bounds reject malformed input as a 422 (not a DuckDB BinderException
    # → 500 on the public agent surface): offset >= 0, limit in [1, 50000]. The
    # upper bound comfortably exceeds the dataset (~37k rows) so it never truncates
    # a legitimate full read while capping a whole-table grab.
    limit: int = Query(default=5000, ge=1, le=50000),
    offset: int = Query(default=0, ge=0),
):
    """The matching tidy Observation rows, returned VERBATIM and self-describing.

    The faithful, unpinned agent access surface (ADR 0004): unlike /api/series,
    it NEVER resolves to one Convention and NEVER 422s on ambiguity — co-locating
    labelled rows across Conventions is not merging. All filters are optional,
    multi-value comma-lists selecting the union; an omitted filter is
    unconstrained. All matching Millésimes are returned (Révisions inline, not
    deduped); both nominal and euros_constants rows unless narrowed. An empty
    match is a normal 200 with []. `total` is the full matched count (truncation
    detection) while `limit`/`offset` slice the page.
    """
    filters = {
        "source": _csv_list(source),
        "indicateur": _csv_list(indicateur),
        "groupe": _csv_list(groupe),
        "concept": _csv_list(concept),
        "unite": _csv_list(unite),
        "millesime": _csv_list(millesime),
        "annee_min": annee_min,
        "annee_max": annee_max,
        "euros_constants": euros_constants,
    }
    rows, total = data.get_observations(**filters, limit=limit, offset=offset)
    return ObservationsResponse(
        query=filters,
        total=total,
        limit=limit,
        offset=offset,
        observations=[Observation(**row) for row in rows],
    )


@app.get("/api/schema", response_model=Schema)
def schema():
    """The machine-readable contract / agent entry point (ADR 0004): the
    Conventions, the per-indicateur value semantics with the `dimensionless` flag
    (in-band ADR 0003), the known Ruptures, the historisation key, and the guard
    rails as English strings. Read-only, public, GET-only."""
    return data.get_schema()
