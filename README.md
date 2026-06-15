# wealth-fr — Concentration du patrimoine en France depuis 2000

Explore, visualize and compare harmonized wealth-concentration series for France
(top shares, Gini, average wealth) across three public sources — **WID**, **INSEE**,
**DGFiP** — while respecting that their measurement **Conventions are not
interchangeable**. See [HANDOFF.md](./HANDOFF.md) for the full product brief and
[CONTEXT.md](./CONTEXT.md) for the domain glossary.

> **Status:** the read path works end to end on a curated/fixture dataset.
> **Done:** pipeline Parquet output (jalon 2), backend `/api/meta` + `/api/series`
> (jalon 3), frontend routing + URL state + dashboard (jalon 4). **Pending:**
> comparison, révisions, live integration, refresh, methodology, export — see the
> jalon roadmap in [HANDOFF.md §9](./HANDOFF.md#9-jalon-roadmap) and epic
> [#2](https://github.com/payouri/wealth-fr/issues/2). Endpoints `/api/compare`,
> `/api/revisions`, `/api/sources`, `/api/export.csv` and the Comparison / Sources
> views are still `TODO(jalon N)` stubs. **No real (live-fetched) Millésime exists
> yet** — that is jalon 6.5.

## Layout

```
wealth-fr/
├── package.json     # root dev runner: `pnpm bootstrap`, `pnpm dev` (concurrently)
├── docker-compose.yml   # prod-style stack: nginx + backend (+ data-profile pipeline)
├── pipeline/        # Python data pipeline (existing, working)
│   ├── build_dataset.py   netfetch.py   Dockerfile
│   ├── data/        # raw sources: WID_data_FR.csv, dgfip_isf_ifi.csv
│   └── out/         # generated CSV / Parquet / XLSX  (gitignored)
├── backend/         # FastAPI + DuckDB  (meta + series live; compare/revisions/sources stubbed)
│   ├── app/         # main.py · data.py · models.py
│   └── Dockerfile
├── frontend/        # React + TS + Tailwind v4 + Vite 8 + Recharts (Dashboard live; Comparison/Sources stubbed)
│   ├── src/         # api/ · components/ · hooks/ · lib/ · views/
│   └── Dockerfile   nginx.conf   # multi-stage build → nginx static + /api proxy
├── .github/workflows/   # ci.yml · security.yml · refresh-data.yml (jalon-7 stub)
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
> `WID 2026` Millésime, ~157k observations). **DGFiP** still loads curated points /
> a local CSV — its live `.xlsx` parser is **jalon 6.5** (pending), along with
> explicit auth-failure fallback ([HANDOFF.md §10](./HANDOFF.md#10-risks--open-questions)).
> The **Parquet** output (jalon 2) is written — the backend prefers Parquet, falls
> back to CSV.

### Backend (meta + series live; compare/revisions/sources stubbed)
```bash
cd backend
pip install -r requirements-dev.txt  # runtime + pytest/ruff/mypy (use requirements.txt for runtime only)
uvicorn app.main:app --reload        # /api/health, /api/meta, /api/series work; compare/revisions/sources are TODO
pytest                                # contract tests for the live endpoints pass; stubbed-endpoint tests stay skipped
```

### Frontend (Dashboard live; Comparison/Sources stubbed)
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

See [HANDOFF.md §6.4](./HANDOFF.md#64-api-contract) and
[`backend/app/models.py`](./backend/app/models.py): `/api/meta`, `/api/series`
(live); `/api/compare`, `/api/revisions`, `/api/sources`, `/api/export.csv` (stubbed,
see the per-jalon status in §6.4).

## Documents

- [AGENTS.md](./AGENTS.md) — rules of engagement for coding agents: commands, gates, traps.
- [HANDOFF.md](./HANDOFF.md) — full product brief, sources, API contract, jalons (source of truth).
- [CONTEXT.md](./CONTEXT.md) — domain glossary and invariants.
