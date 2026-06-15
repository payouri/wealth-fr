# The agent access surface returns labelled cross-Convention rows, unpinned

Every *resolving* endpoint built so far collapses the raw tidy data to one
Convention and one Millésime and refuses (`422`) when a query still spans more
than one Convention — `/api/series` (ADR 0002), `/api/compare` (ADR 0003), and
`/api/export.csv` all share that guard. That strictness is correct for a
**human reader** plotting a line: a chart axis that silently mixes `adulte/net`
with `menage/brut`, or nominal with deflated euros, is the apples-to-oranges
misread the Convention guard rail exists to prevent.

A new consumer changes the calculus. We are adding a programmatic / agent
access surface (`/api/observations` + `/api/schema`) so an agent can pull the
data and reason over it itself (correlate, trend, summarise) — the analysis
lives in the agent, the backend stays a faithful data server. For that consumer,
pinning to one Convention per call is the wrong shape: it forces an agent to
disambiguate before it can read anything, and turns "give me DGFiP's history"
into a `422`/retry dance plus N single-series calls against a ~37k-row table.

The key distinction this ADR rests on: **co-locating self-describing rows is not
merging.** The guard rail forbids *aggregating or comparing* across Conventions
(CONTEXT.md). It does not forbid *returning* observations from several
Conventions in one response, as long as every row still carries its own `unite`,
`concept_patrimoine`, `millesime_source`, and `date_extraction`. Nothing is
collapsed; the Convention travels with each value.

## Decision

- **`/api/observations` never resolves and never `422`s on ambiguity.** It
  streams the matching tidy rows verbatim — spanning whatever Conventions,
  Millésimes, and `unite_valeur` (nominal *and* `euros_constants_2021`) the
  filter matches — each row self-describing. There is no `concept`-is-required
  rule and no `AmbiguousConvention`; the resolver guard (`_resolve_query`) is
  deliberately *not* on this path.
- **Filters are optional, multi-value (comma lists)** on `source`,
  `indicateur`, `groupe`, `concept`, `unite`, `millesime`, plus an
  `annee_min`/`annee_max` range and an optional `euros_constants` narrow.
  Omitted dimension = no constraint.
- **Bounded, not paginated-by-cursor.** Default `limit` (~5000) + `offset`, and
  the response carries the `total` matched count so a consumer can detect
  truncation and page if it really wants a large slice. The dataset is ~37k
  rows; a cursor protocol would be overkill.
- **The guard rail moves in-band, it is not dropped.** `/api/schema` publishes
  the Conventions, the per-`indicateur` value semantics with a `dimensionless`
  flag (derived from `unite_valeur`: `%`/`indice` are dimensionless and
  cross-source-comparable in *shape*; `euros*` are levels; `effectif` is a
  count), the Ruptures, the historisation key, and the guard rails as
  machine-readable English. An agent learns "never merge across Convention;
  euros_constants only on levels; revisions are append-only" from the API
  itself, rather than only from CONTEXT.md out-of-band. Responsibility for not
  merging shifts to the consumer, and the contract it needs to honour that
  responsibility is now discoverable.

## Consequences

- There are now **two stances by consumer**, on purpose: resolving + strict for
  the UI (`/api/series`, `/api/compare`, `/api/export.csv`), faithful + unpinned
  for agents (`/api/observations`). A future reader who wonders "why doesn't the
  bulk endpoint `422` like `/api/series`?" finds the answer here.
- **These models are not mirrored into `frontend/src/api/types.ts`.** The
  "two mirrors must agree" rule (AGENTS.md) governs the *UI* contract, and the
  frontend does not consume these endpoints. A one-line note in
  `backend/app/models.py` marks the carve-out so it reads as deliberate, not
  forgotten. If a UI surface later consumes them, mirror them then.
- The `dimensionless` flag in `/api/schema` is the in-band encoding of ADR 0003:
  it tells an agent which indicateurs may be overlaid across Sources (in shape)
  and which euro-levels may not — the same line ADR 0003 draws for the human
  comparison view, exposed so an agent can self-police.
- CONTEXT.md is unchanged: no new *domain term* is introduced. "Observation",
  "Convention", "Révision", and "Rupture" already name everything these surfaces
  expose; the endpoints are new views over existing language.
