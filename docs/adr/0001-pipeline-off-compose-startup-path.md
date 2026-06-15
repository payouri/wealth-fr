# Keep the data pipeline off the compose startup path

The docker-compose stack serves the harmonized dataset to the backend via a
**read-only bind mount of `pipeline/out`**, and exposes the pipeline only as a
`--profile data` service that is run on demand — it is deliberately **not** part
of the default `docker compose up`.

## Context

The obvious design is an init container: a `pipeline` service runs
`build_dataset.py` into a shared volume, and the backend `depends_on` it with
`service_completed_successfully`, giving a fully self-contained `up`. We rejected
that because, **at the time of this decision**, the pipeline's network calls to
WID/DGFiP had **only ever been tested against simulated responses, never live
servers** (restricted dev network), and require secrets (`WID_API_KEY_B64`,
`DGFIP_IFI_XLS_URL`). Putting that on the startup critical path means onboarding
and every `up` would block or fail whenever a source is unreachable, throttled,
or a secret is missing.

## Decision

Decouple data *generation* from data *serving*. The backend only reads whatever
Parquet/CSV already exists in `pipeline/out` (bind-mounted read-only). Dataset
(re)generation is an explicit, opt-in step (`docker compose --profile data run
pipeline`, or the existing host pipeline flow). Onboarding is therefore:
generate the dataset once, then `docker compose up`.

## Consequences

- A fresh `docker compose up` with an empty `pipeline/out` brings up a backend
  whose data routes (`/api/meta`, `/api/series`) return empty/no-data until a
  dataset is generated — surfaced in the onboarding docs.
- This is the deliberate answer to the future "why isn't the pipeline just an
  init container?" — keep generation off the `up` path.

## Update (2026-06)

The decision stands. The original "never tested against live servers" rationale is
now partly overtaken: the **WID** API has been run live in production (a real
`WID 2026` Millésime, ~157k observations), so the WID half of the once-feared
network risk is validated. **DGFiP** still loads curated points / a local CSV (the
live `.xlsx` parser is jalon 6.5, pending), and INSEE is curated by design. In
production, generation is realised via Coolify — a one-off `--profile data` run
plus a Scheduled Task that `docker exec`s the always-on `pipeline-runner`
(`docker-compose.production.yml`) into a persistent `dataset` volume — which keeps
generation off the deploy path exactly as this ADR intends. The original jalon
reference (jalon 3) for live integration is now jalon 6.5.
