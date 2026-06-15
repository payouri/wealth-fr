# wealth-fr — Concentration du patrimoine en France depuis 2000

Explore, visualize and compare harmonized wealth-concentration series for France
(top shares, Gini, average wealth) across three public sources — **WID**, **INSEE**,
**DGFiP** — while respecting that their measurement **Conventions are not
interchangeable**. See [CONTEXT.md](./CONTEXT.md) for the domain glossary and
[AGENTS.md](./AGENTS.md) for the rules of engagement.

> **Status:** the full reader-facing product is implemented (jalons 2–6, 8, 9).
> **Done:** pipeline Parquet output (jalon 2); the backend endpoints `/api/meta`,
> `/api/series`, `/api/compare`, `/api/revisions`, `/api/sources`, `/api/export.csv`
> (jalons 3, 5, 6, 8, 9); the frontend Dashboard, Comparison and Sources &
> méthodologie views with URL state and chart PNG export (jalons 4, 5, 8, 9). A real
> `WID 2026` Millésime is live in production. **Open:** the live prod DGFiP fetch run
> ([#12](https://github.com/payouri/wealth-fr/issues/12)) and the data-coverage
> backlog ([#13](https://github.com/payouri/wealth-fr/issues/13)); the roadmap epic
> [#2](https://github.com/payouri/wealth-fr/issues/2) is closed. Scheduled refresh
> (former jalon 7) runs as a **Coolify Scheduled Task**, not a GitHub Action — see
> [Production](#production) and
> [ADR 0001](./docs/adr/0001-pipeline-off-compose-startup-path.md).

## Layout

```
wealth-fr/
├── package.json     # root dev runner: `pnpm bootstrap`, `pnpm dev` (concurrently)
├── docker-compose.yml   # prod-style stack: nginx + backend (+ data-profile pipeline)
├── pipeline/        # Python data pipeline (existing, working)
│   ├── build_dataset.py   netfetch.py   Dockerfile
│   ├── data/        # raw sources: WID_data_FR.csv, dgfip_isf_ifi.csv
│   └── out/         # generated CSV / Parquet / XLSX  (gitignored)
├── backend/         # FastAPI + DuckDB  (meta · series · compare · revisions · sources · export.csv)
│   ├── app/         # main.py · data.py · models.py
│   └── Dockerfile
├── frontend/        # React + TS + Tailwind v4 + Vite 8 + Recharts (Dashboard · Comparison · Sources & méthodologie)
│   ├── src/         # api/ · components/ · hooks/ · lib/ · views/
│   └── Dockerfile   nginx.conf   # multi-stage build → nginx static + /api proxy
├── .github/workflows/   # ci.yml · security.yml
├── CONTEXT.md       # domain glossary (the data contract in words)
└── docs/adr/        # architecture decision records
```

## Run both servers at once (local dev)

The fastest inner loop — backend + frontend together, hot-reload, no Docker:

```bash
pnpm bootstrap   # one-time: create backend/.venv, install backend + frontend deps
pnpm dev         # runs uvicorn (:8000) and vite (:5173) concurrently; Ctrl-C stops both
```

`pnpm dev` prefixes output as `api`/`web`. The frontend proxies `/api → :8000`
(see `frontend/vite.config.ts`), so just open http://localhost:5173.

## Docker (production-style stack)

`docker compose` builds the frontend to static assets served by **nginx**, which
also reverse-proxies `/api` to the backend — one entry port, same-origin (no CORS):

```bash
docker compose up --build        # open http://localhost:8080
```

The backend serves whatever harmonized dataset exists in `pipeline/out/`
(bind-mounted read-only). The data **pipeline is deliberately not part of
`up`** — generate the dataset on demand with the `data` profile:

```bash
# UID/GID keep pipeline-written files owned by you, not root (see docker-compose.yml).
UID=$(id -u) GID=$(id -g) docker compose --profile data run --rm pipeline                     # default: --annee-min 2000
UID=$(id -u) GID=$(id -g) docker compose --profile data run --rm pipeline --download --full   # needs secrets in .env
```

Why the pipeline is off the startup path: see
[docs/adr/0001-pipeline-off-compose-startup-path.md](./docs/adr/0001-pipeline-off-compose-startup-path.md).

## Quick start (per component)

### Pipeline
```bash
cd pipeline
pip install -r requirements.txt
# Option A — API (needs WID_API_KEY_B64; see .env.example):
python build_dataset.py --download --full
# Option B — local file, no key: drop data/WID_data_FR.csv, then:
python build_dataset.py --annee-min 2000
# Output: dataset_concentration_patrimoine_fr.csv + .parquet (+ dated .xlsx)
```
> ⚠️ As of 2026-06 the **WID** API has been run **live in production** (a real
> `WID 2026` Millésime, ~157k observations). **DGFiP** now parses the real ISF/IFI
> workbooks (`pipeline/dgfip_parse.py`, jalon 6.5) — there is no single URL, so a
> registry (`DGFIP_SOURCE_URLS`, default = 3 IFI `/node/` links + the ISF
> data.gouv.fr resource — see [`.env.example`](./.env.example)) is fetched as a lot,
> with fallback to the curated CSV / pre-filled points on any download or parse
> failure. A live prod run of that fetch is still open
> ([#12](https://github.com/payouri/wealth-fr/issues/12)).
> The **Parquet** output (jalon 2) is written — the backend prefers Parquet, falls
> back to CSV.

### Backend (all data endpoints live)
```bash
cd backend
pip install -r requirements-dev.txt  # runtime + pytest/ruff/mypy (use requirements.txt for runtime only)
uvicorn app.main:app --reload        # /api/health + meta/series/compare/revisions/sources/export.csv
pytest                                # contract tests for every endpoint pass
```

### Frontend (Dashboard · Comparison · Sources & méthodologie)
```bash
cd frontend
pnpm install
pnpm dev                              # http://localhost:5173, proxies /api -> :8000
```

## Key invariants (do not break)

- **Convention guard rail.** `unite` + `concept_patrimoine` qualify every value.
  Never aggregate or compare across Conventions; expose them as first-level
  filters and label every plotted line. (CONTEXT.md)
- **Append-only historisation.** Sources revise retroactively. Observations are
  never overwritten — both millésimes of a revised value coexist.
- **Deflation only on levels.** `euros_constants` rows are added alongside
  nominal ones; shares (%) and Gini are never deflated.
- **Traceability is a feature.** `source`, `millesime_source` and
  `date_extraction` stay visible for every displayed figure.

## API contract

The contract **is the code**: the Pydantic models in
[`backend/app/models.py`](./backend/app/models.py) and their TS mirror in
[`frontend/src/api/types.ts`](./frontend/src/api/types.ts). Endpoints (all live):
`/api/meta`, `/api/series`, `/api/compare`, `/api/revisions`, `/api/sources`,
`/api/export.csv`. Query-param / `422` semantics live in the FastAPI route
signatures ([`backend/app/main.py`](./backend/app/main.py)) and
[ADR 0002](./docs/adr/0002-series-endpoint-resolves-one-convention-one-millesime.md).

## Production

In production the app runs on **Coolify**. The dataset (CSV + Parquet) is **not**
committed to the repo — it lives in a Coolify-managed persistent `dataset` volume
that the backend reads (see
[`docker-compose.production.yml`](./docker-compose.production.yml)). The volume is
refreshed by a **Coolify Scheduled Task** that `docker exec`s the always-on
`pipeline-runner` container with `--download --full`:

```bash
docker exec <pipeline-runner> python build_dataset.py --download --full
```

There is **no GitHub Action** that refreshes or commits the data — generation stays
off the deploy path by design. See
[ADR 0001](./docs/adr/0001-pipeline-off-compose-startup-path.md) for why (and for
the repo→volume decision).

## Documents

- [AGENTS.md](./AGENTS.md) — rules of engagement for coding agents: commands, gates, traps.
- [CONTEXT.md](./CONTEXT.md) — domain glossary and invariants.
- [docs/adr/](./docs/adr/) — architecture decisions and *why*.
