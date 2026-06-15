# The API contract is backend-canonical: frontend types are generated from OpenAPI

The contract used to live in **two hand-written mirrors** — the Pydantic models in
`backend/app/models.py` and the TypeScript types in `frontend/src/api/types.ts` —
kept in sync only by developer discipline. They drifted: the TS `Concept` union went
stale (missing the INSEE `brut_hors_reste` / `net_hors_reste` variants), the backend
field was a bare `concept_patrimoine: str` with no enum at all, and the
`422 ambiguous_convention` body (`AmbiguousConventionDetail` / `ConventionChoice`)
existed *only* in TypeScript — hand-built as a dict in an exception handler and absent
from the OpenAPI schema. We make the **backend canonical** and **generate** the
frontend types from the FastAPI-emitted OpenAPI, so a generated file can no longer
disagree with its source.

## Context

The contract is really two contracts with opposite natures:

- **Structural** — response *shapes*, query params, the `422` body. Static, and
  FastAPI already emits it as OpenAPI for free.
- **Vocabulary** — *which* `concept` / `groupe` strings exist. This is **data-driven
  by design**: `data.py` computes the available values at runtime with
  `SELECT DISTINCT …`, and the `Meta` lists + `availability` map exist precisely so
  the UI discovers the vocabulary rather than hardcoding it. The stale TS `Concept`
  union was a hand-typed guess at the data — which is *why* it drifted.

A shared/neutral IDL (TypeSpec, JSON-Schema-first) generating both sides was
considered and rejected: the Pydantic side carries docstrings and the `422` *runtime*
rule that no static schema can express, FastAPI's OpenAPI is free, and a third
canonical artifact buys nothing over backend-canonical for a Python+TS pair with no
other consumers.

## Decision

- **Backend (Pydantic) is the single source of truth.** FastAPI emits OpenAPI;
  `frontend/src/api/types.ts` becomes generated output (`openapi-typescript`), never
  hand-edited. The hand-written `client.ts` / `error.ts` stay, importing the generated
  types (types-only codegen — no generated client or SDK).
- **Hybrid vocabulary split.** `Source`, `Unite`, `Indicateur` are **closed** —
  Python `Literal`s used in both models and route params, so they become OpenAPI enums
  (and FastAPI `422`s an unknown value for free). `concept_patrimoine` and `groupe`
  stay **open** strings, validated at runtime against `/api/meta`, matching the
  existing `_distinct` / `availability` design. `Indicateur` is closed because the six
  measures are a curated vocabulary, not raw data granularity.
- **The `422` body becomes real Pydantic models** declared via
  `responses={422: {"model": …}}` on the resolving routes, so it lands in OpenAPI and
  is generated for the frontend.
- **Drift is gated in CI.** A committed `openapi.json` is the cross-job interface: the
  Python job regenerates it and `git diff --exit-code`s (guards Pydantic → schema);
  the frontend job regenerates `types.ts` from the committed JSON and `git diff`s
  (guards schema → TS, stays pure-Node).

Implementation is tracked in
[#17](https://github.com/payouri/wealth-fr/issues/17); AGENTS.md and the
`models.py` / `types.ts` docstrings (which still describe "two mirrors that must
agree") are updated there as the codegen lands.

## Consequences

- This **reverses** the previously documented stance that "the contract *is* the
  code, in two mirrors — change one → change the other." After this, you change
  Pydantic only; `types.ts` is build output.
- A future reader wondering "why is `Source` a closed enum but `concept_patrimoine` a
  bare `string`?" finds the answer here: the vocabulary is deliberately data-driven
  and discovered via `/api/meta`, while the stable axes are curated. It is a guard-rail
  decision, not an inconsistency to "fix".
- Adding a new `Source` / `Unite` / `Indicateur` is now an intentional schema change
  (Pydantic `Literal` + regenerate). Adding a new `concept` / `groupe` needs **no**
  code change — it flows through `/api/meta` automatically.
