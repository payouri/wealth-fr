# `/api/series` returns exactly one Convention and one Millésime

A `Series` response carries a single `unite`, `concept_patrimoine`, and
`millesime_source` (see `backend/app/models.py`). The raw tidy data offers
*several* candidates per query — a Source can span more than one Concept (DGFiP:
`total` ≤2017, `immobilier` ≥2018), and a Révision keeps multiple Millésimes for
the same `HIST_KEYS`. So the endpoint must collapse both dimensions, and we chose
to do it **strictly** rather than guess.

## Decision

- **Concept is a required query param.** It genuinely varies within a Source
  (across a Rupture), so it cannot be inferred. This deviates from
  HANDOFF.md §6.4, which listed `concept` as optional — §6.4 has been corrected.
- **Unité is derived from `source`**, not required. It is one-per-source in all
  three loaders (WID=`adulte`, INSEE=`menage`, DGFiP=`foyer_fiscal`) and echoed
  back in the response.
- **Ambiguity is a `422`, never a silent pick.** If a query still resolves to
  more than one Convention, the endpoint refuses and returns the available
  choices, honoring the CONTEXT.md guard rail (never merge or silently drop a
  Convention). A valid query matching zero rows is a normal `200` with empty
  `points`.
- **Millésime defaults to the latest by `date_extraction`**, with an optional
  `millesime` param to pin an older vintage. The current best-known series by
  default; `/api/revisions` owns the old-vs-new diff.
- **Ruptures come from a small known-ruptures table in the backend** (e.g.
  `DGFiP → (2018, "ISF (total) → IFI (immobilier)")`), surfaced when the rupture
  year falls in the requested range. The data's `notes` stay as raw provenance;
  we do not parse free-form prose.

## Consequences

- The two contract mirrors (`backend/app/models.py` ↔
  `frontend/src/api/types.ts`) and the frontend client must mark `concept`
  required; both trace to the corrected HANDOFF.md §6.4.
- The frontend must obtain a valid `concept` (from `/api/meta`) before calling
  `/api/series`, and must handle the `422`-with-choices response as a
  "pick a Convention" prompt rather than an error.
