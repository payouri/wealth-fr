# Keep the data pipeline off the compose startup path

The docker-compose stack serves the harmonized dataset to the backend via a
**read-only bind mount of `pipeline/out`**, and exposes the pipeline only as a
`--profile data` service that is run on demand — it is deliberately **not** part
of the default `docker compose up`.

## Context

The obvious design is an init container: a `pipeline` service runs
`build_dataset.py` into a shared volume, and the backend `depends_on` it with
`service_completed_successfully`, giving a fully self-contained `up`. We rejected
that because the pipeline's network calls to WID/DGFiP were **only ever tested
against simulated responses, never live servers** (restricted dev network — see
README and `pipeline/build_dataset.py`), and require secrets (`WID_API_KEY_B64`,
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
  with no data — acceptable today (data routes are still stubs) and surfaced in
  the onboarding docs.
- This is the deliberate answer to the future "why isn't the pipeline just an
  init container?" — do not move it onto the `up` path until the live
  WID/DGFiP integration (jalon 3) is actually tested.
