# INSEE is fetched live from Melodi; hors-reste is a separate Convention; we self-deflate

INSEE used to be the one **hand-curated** Source: three pasted Observations (a 1998
and a 2021 Gini, a 2021 top-50 share). The project documentation asserted "INSEE is
curated by design" / "no dedicated API for the aggregates". That assertion is now
**false**: INSEE publishes the *Enquête Patrimoine / Histoire de vie et patrimoine*
(HVP) aggregates through its public **Melodi** API (dataset `DS_ENQPAT_DET`, no
auth). A reader opening the INSEE view therefore saw a near-empty Source while WID
ran live and DGFiP parsed real workbooks. We make INSEE a real, refreshable Source.

This ADR **amends** [ADR 0001](./0001-pipeline-off-compose-startup-path.md)'s
"INSEE is curated by design" clause.

## Context

Three design questions had to be settled, each with a landmine:

- **The Convention boundary.** INSEE's measures span more than one wealth concept:
  the all-inclusive `brut`/`net`, and the *hors reste* variants `brut_hors_reste` /
  `net_hors_reste` that exclude INSEE's residual asset category. These are
  **different quantities** — the apparent "0.662 vs 0.645" Gini "revision" was in
  fact a Convention mix-up (hors-reste vs all-inclusive brut), not a Révision.
- **The deflation base.** INSEE publishes its own constant-euro series, but on a
  different base than the project's. Mixing bases across Sources would make
  cross-Source level comparison dishonest.
- **An upstream mislabel.** Melodi's metadata describes `GINI_PATBRUT_HR` as "net";
  it is authoritatively **brut hors reste** per INSEE's publications.

## Decision

- **Live fetch, three-tier fallback.** INSEE is fetched live from Melodi when
  `--download` is set (`netfetch.download_insee_melodi`), parsed by a new
  `pipeline/insee_parse.py` (sibling of `dgfip_parse`); else a cached local file is
  parsed; else a small curated **stub** is used (the former curated points,
  relabelled `brut_hors_reste` to be truthful). The build never silently drops the
  Source. The dataset id is env-overridable (`INSEE_MELODI_DATASET`). The network
  layer is thin and **not** exercised against the live API in CI (same posture as
  WID); correctness lives in the parser/loader tests against synthetic/cached inputs.
- **Hors-reste is modelled as separate Conventions.** `brut_hors_reste` and
  `net_hors_reste` are first-class `concept_patrimoine` values, never merged with
  the all-inclusive `brut`/`net` (non-negotiable #1). Selecting INSEE without a
  pinned Concept returns the same `422` Convention chooser DGFiP already triggers.
  Coverage is asymmetric and not over-promised: Gini and shares exist for the
  brut-family only; `net`/`net_hors_reste` carry level series only.
- **We self-deflate to the project base.** Only nominal (current-euro, `…_COUR`)
  levels are ingested; the pipeline's existing level-deflation step produces the
  constant-euro Observations, so INSEE shares one base with WID and DGFiP. INSEE's
  own constant-euro series (different base) is **not** ingested. The CPI table is
  extended to cover the deep waves (1998, 2004, 2010) so they are not dropped.
- **The metadata mislabel is handled deliberately in code.** `GINI_PATBRUT_HR` is
  routed to `brut_hors_reste` with a comment, so nobody "fixes" it back to net.

## Consequences

- INSEE is refreshed by the same `--download` pipeline run as WID and DGFiP; a
  later fetch after INSEE restates a wave yields a new Millésime, so the existing
  Révision-detection surfaces the change with both Observations retained.
- The contract gains two open `concept_patrimoine` values (`brut_hors_reste`,
  `net_hors_reste`). Per [ADR 0005](./0005-api-contract-is-backend-canonical-codegen.md)
  the Concept axis is data-driven and discovered via `/api/meta`, so no UI wiring
  is required — the dynamic Concept chooser and Convention legend absorb them.
- This delivers the INSEE-HVP portion of the data-coverage backlog
  ([#13](https://github.com/payouri/wealth-fr/issues/13)); the pre-2017 ISF
  indicator portion of #13 remains DGFiP scope and stays open.
