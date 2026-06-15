# Handoff — Webapp "Concentration du patrimoine en France depuis 2000"

> Handoff document for a coding agent building a web application on top of the
> existing Python data pipeline. Everything below reflects the real state of the
> code and the methodological decisions already made.
>
> **Progress (2026-06):** the scaffold is no longer structure-only. Jalons 2
> (Parquet output), 3 (backend `/api/meta` + `/api/series`) and 4 (frontend
> routing + URL state + dashboard) are **done** (GitHub issues #3, #1, #4). The
> remaining roadmap lives in the **epic [#2](https://github.com/payouri/wealth-fr/issues/2)**;
> per-jalon status is tracked in §9. Sections §6.2/§6.4/§9 below are kept current;
> their original "to build" proposals now read as the realised design where a
> jalon is marked done.

---

## 1. Context and goal

The project aims to surface the **concentration of wealth and assets in France
since the 2000s** from **harmonized public data**. The central difficulty: wealth
inequality concentrates at the top of the distribution, exactly where sample
surveys underestimate reality. The dataset therefore combines several sources with
differing Conventions, while tracing those Conventions explicitly.

The web app must let users **explore and visualize** these series (top 10% / 1% /
0.1% shares, the Gini index, average wealth), **compare the sources**, and make the
**methodological breaks** legible (notably ISF → IFI in 2018).

---

## 2. Current state: the data pipeline

Two working, tested Python files. Originally validated only against simulated
responses (restricted dev network), but as of **2026-06 the WID API has been run
live in production** — a real `WID 2026` Millésime (~157k observations) now exists
in the prod `dataset` volume. **DGFiP** still loads curated points / a local CSV
(the live `.xlsx` parser is jalon 6.5, pending); **INSEE** is curated by design.

### 2.1 `build_dataset.py` — orchestrator

Builds the harmonized, historised dataset, then writes it to CSV (cumulative),
**Parquet (cumulative, the backend's preferred fast path — added in jalon 2)** and
Excel (dated snapshot).

Key functions:

| Function                          | Role                                                                 |
| --------------------------------- | -------------------------------------------------------------------- |
| `load_wid(path, …)`               | Reads a local WID file (`WID_data_FR.csv`, `;` separator) → tidy     |
| `_wid_rows_to_tidy(rows, …)`      | Converts raw WID API rows → tidy                                     |
| `load_insee(…)`                   | Pre-filled (curated) official INSEE points → tidy                    |
| `load_dgfip(path, …)`             | ISF/IFI: external CSV if present, otherwise pre-filled points → tidy |
| `_stamp(rows, date, millesime)`   | Adds the historisation fields                                        |
| `deflate_levels(df, base_year)`   | Converts levels (€) to constant euros (alters neither % nor Gini)    |
| `harmonize(*frames, annee_min)`   | Stacks the sources, filters the period, orders, validates the schema |
| `write_outputs(df, stem, append, out_dir)` | Writes cumulative CSV + cumulative Parquet + dated Excel, **detects revisions** |
| `main(argv)`                      | CLI                                                                  |

CLI options: `--wid`, `--fiscal`, `--annee-min`, `--out-dir`, `--base-deflation`,
`--millesime-wid|insee|dgfip`, `--download`, `--full`, `--wid-api-key`,
`--dgfip-url`, `--no-append`.

### 2.2 `netfetch.py` — network layer

| Function                                              | Role                                                           |
| ----------------------------------------------------- | -------------------------------------------------------------- |
| `_http_get(url, …)`                                   | Robust GET: timeout + exponential retries                      |
| `fetch_wid(api_key_b64, areas, codes, …)`             | WID API call (restricted indicator list)                       |
| `fetch_wid_available(api_key_b64, areas, sixlets, …)` | Discovers the wealth percentiles available for a country       |
| `fetch_wid_full(api_key_b64, areas, …)`               | API-side "full file": all wealth percentiles, in batches of 40 |
| `download_file(url, dest, …)`                         | Direct download of a file (DGFiP Excel), no key                |

---

## 3. Data model (the "tidy" schema)

One row = one Observation. This is the central **data contract** of the app.

| Column               | Type  | Description                                    | Examples                                                                           |
| -------------------- | ----- | ---------------------------------------------- | ---------------------------------------------------------------------------------- |
| `annee`              | int   | Year of the Observation                        | `2021`                                                                             |
| `source`             | str   | Producer                                       | `WID`, `INSEE`, `DGFiP`                                                            |
| `concept_patrimoine` | str   | Wealth concept measured                        | `net`, `brut`, `total` (ISF), `immobilier` (IFI)                                   |
| `unite`              | str   | Statistical unit                               | `adulte`, `menage`, `foyer_fiscal`                                                 |
| `groupe`             | str   | Sub-population                                 | `ensemble`, `top10`, `top1`, `top0_1`, `bottom50`, `redevables`, …                 |
| `indicateur`         | str   | The measure                                    | `part_patrimoine`, `gini`, `patrimoine_moyen`, `seuil`, `nb_foyers`, `impot_moyen` |
| `valeur`             | float | Numeric value                                  | `27.0`                                                                             |
| `unite_valeur`       | str   | Unit of the value                              | `%`, `indice`, `euros`, `euros_constants_2021`, `effectif`                         |
| `euros_constants`    | bool  | Deflated value?                                | `true`/`false`                                                                     |
| `date_extraction`    | date  | **[Historisation]** date of the pull           | `2026-06-12`                                                                       |
| `millesime_source`   | str   | **[Historisation]** version of the source file | `WID 2026`, `DGFiP 2024`                                                           |
| `notes`              | str   | Source variable, treatments, breaks            | `WID API shweal_p99p100_992_j`                                                     |

**Historisation key** (`HIST_KEYS`): `annee, source, concept_patrimoine,
unite, groupe, indicateur`. A Révision = same key + different value + different
`millesime_source`. Both versions coexist in the cumulative CSV (never
overwritten).

> ⚠️ **Comparability**: `unite` and `concept_patrimoine` are **not
> interchangeable** across sources. Never naively aggregate/compare WID
> (adulte/net) with INSEE (ménage/brut) or DGFiP (foyer fiscal). The UI must
> filter/segment by these two dimensions.

---

## 4. The sources (ingestion detail)

| Source              | Convention                           | Coverage                                                | Access                                 | Notes                                                       |
| ------------------- | ------------------------------------ | ------------------------------------------------------- | -------------------------------------- | ----------------------------------------------------------- |
| **WID.world**       | adulte / **net** wealth, equal-split | long annual series                                      | **API** (key) or manual ZIP file       | Reference for the top (combines fiscal + national accounts) |
| **INSEE** (HVP)     | ménage / **brut** wealth             | survey waves (1998, 2004, 2010, 2015, 2018, 2021, 2023) | curated points / FPR files / CASD      | No dedicated API for the aggregates                         |
| **DGFiP** (ISF/IFI) | foyer fiscal                         | annual                                                  | Excel on impots.gouv.fr / data.gouv.fr | **2018 break**                                              |

### 4.1 WID — API details

- Endpoint: `https://rfap9nitz6.execute-api.eu-west-1.amazonaws.com/prod/`
- Data: `…/countries-variables?countries=FR&variables=<codes>&years=all`
- Discovery: `…/countries-available-variables?countries=FR&variables=<sixlets>`
- Header: `x-api-key: <base64 key>` (see §8; **sent verbatim, no re-encoding**)
- Code grammar: `{sixlet}_{percentile}_{age}_{pop}`
  e.g. `shweal_p99p100_992_j` = net wealth share, top 1%, adults 20+, equal-split.
- Wealth sixlets: `shweal` (share), `ahweal` (average), `thweal` (threshold), `ghweal` (Gini).
- Data response: `{ code: [ { pays: { "values": [[year, value], …], "meta": {…} } } ] }`
- WID shares are fractions in `[0,1]` → multiply by 100 for %.

### 4.2 DGFiP — the ISF → IFI break (methodologically critical)

Up to 2017, the **ISF** taxed *all* wealth (`concept_patrimoine = total`). From
2018, the **IFI** covers real estate only (`concept_patrimoine = immobilier`).
**Comparing any pre-2018 amount with a post-2018 amount without filtering on the
concept is an error.** The pipeline already encodes this; the UI must **annotate
it visually** (marker on 2018).

---

## 5. Key decisions and learnings (to respect)

1. **Conventions traced in the schema**: `unite` + `concept_patrimoine` are
   structural. Every layer (DB, API, UI) must preserve them and expose them as
   first-level filters.
2. **Historisation of revisions**: append-only, never overwrite. Sources revise
   retroactively (WID recomputes past years). The `date_extraction` +
   `millesime_source` pair lets you trace/diff.
3. **WID API key**: a sequence of 30 raw bytes, transmitted as **raw base64**.
   Re-encoding it breaks auth. It is a public key embedded in an open-source
   package → keep it configurable (env), and expect it to rotate and be
   rate-limited.
4. **No static URL for the WID "full file"**: the portal ZIP is generated
   dynamically. The programmatic path = the API (discovery + batched fetch). That
   is what `fetch_wid_full` does.
5. **Deflation**: applies only to levels (€), never to shares (%) or Gini.
   Generate `euros_constants=true` rows in addition, without destroying the
   nominal ones.

---

## 6. Web application to build

### 6.1 Product goals

- Visualize the evolution of the **top shares** (top 10/1/0.1%) and the **Gini**
  since 2000.
- **Compare the sources** side by side (respecting the Conventions).
- Toggle **nominal ↔ constant euros** on levels.
- **Annotate the breaks** (2018 ISF→IFI) and millésime changes.
- Allow **export** (CSV/PNG) and **sharing** of a filtered view.

### 6.2 Stack (realised — see the Appendix for divergences from the original proposal)

- **Data**: the existing Python scripts are the ingestion layer. ✅ Parquet output
  added beside the CSV for performance (jalon 2).
- **Backend**: ✅ **FastAPI** (Python) reusing the pipeline and pandas directly.
  Storage: **DuckDB** over the harmonized file (Parquet preferred, CSV fallback) —
  sufficient, the volume is small (a few thousand rows).
- **Frontend**: ✅ **React + TypeScript + Vite + Tailwind v4**, charting via
  **Recharts** (not visx). Server state via **TanStack Query**; routing + URL
  state via **react-router-dom**.
- **Scheduled refresh**: ✅ in production this is a **Coolify Scheduled Task** that
  `docker exec`s the always-on `pipeline-runner` container
  (`python build_dataset.py --download --full`), writing the persistent `dataset`
  volume the backend reads — see `docker-compose.production.yml`. The dataset is
  **not** committed to the repo (artifacts are gitignored; the volume is the store
  of record on the server). The original jalon-7 GitHub Action approach is
  superseded by this and parked (a stub `refresh-data.yml` remains).

### 6.3 Tree (realised — pnpm workspace, single host via docker compose)

```
wealth-fr/                    # GitHub repo payouri/wealth-fr (local dir: eco_stats_viewer)
├── pipeline/                 # ingestion code
│   ├── build_dataset.py
│   ├── netfetch.py
│   ├── requirements.txt
│   ├── Dockerfile            # opt-in `--profile data` service (ADR 0001)
│   ├── data/                 # WID_data_FR.csv, dgfip_isf_ifi.csv (raw sources)
│   └── out/                  # dataset_*.csv + .parquet + dated .xlsx (gitignored; in prod the data lives in a Coolify volume)
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI routes
│   │   ├── data.py           # parquet -> DuckDB loading, queries, resolver
│   │   └── models.py         # Pydantic schemas (see contract §6.4)
│   ├── tests/                # test_contract.py, test_resolver.py, test_meta.py, …
│   └── Dockerfile
├── frontend/                 # React 19 + TS + Tailwind v4 + Vite
│   ├── src/
│   │   ├── api/              # typed client (client.ts) + types.ts (contract mirror)
│   │   ├── components/       # SeriesChart (Recharts), FilterBar, figure, ui/ (shadcn)
│   │   ├── hooks/            # useDashboardParams (URL state), usePrefersReducedMotion
│   │   ├── lib/              # domain.ts (labels/formatting), utils.ts
│   │   └── views/            # Dashboard (real), Comparison + SourcesMethodo (stubs)
│   ├── Dockerfile            # nginx serves the built SPA, proxies /api
│   └── package.json
├── docs/adr/                 # 0001 pipeline-off-compose, 0002 series resolution, 0003 compare scope
├── docker-compose.yml        # backend + frontend (+ pipeline under profile data)
├── package.json              # pnpm workspace root: bootstrap / dev / api / web
├── .github/workflows/        # ci.yml, security.yml, refresh-data.yml (jalon-7 stub: builds but does not yet commit)
├── HANDOFF.md                # this document
├── AGENTS.md / CONTEXT.md / PRODUCT.md / DESIGN.md / README.md
```

### 6.4 API contract

Status: ✅ implemented · ⏳ stubbed (`raise NotImplementedError` / `TODO(jalon N)`) ·
✖ not yet defined. The Pydantic models for every row below already exist in
[backend/app/models.py](./backend/app/models.py) and their TS mirrors in
[frontend/src/api/types.ts](./frontend/src/api/types.ts) — only the handlers are pending.

| Status | Method | Endpoint          | Description                                                                                                 |
| ------ | ------ | ----------------- | ----------------------------------------------------------------------------------------------------------- |
| ✅      | `GET`  | `/api/meta`       | Value lists: sources, indicateurs, groupes, conventions, millésimes                                         |
| ✅      | `GET`  | `/api/series`     | Filtered series. Query: `source, indicateur, groupe, concept` **(required)**`, unite` (optional, derived from `source`)`, annee_min, annee_max, euros_constants, millesime`. One Convention + one Millésime; ambiguous Conventions → `422` with choices (ADR 0002). |
| ⏳ jalon 5 | `GET`  | `/api/compare`    | Same indicateur/groupe across several sources (dimensionless only — ADR 0003)                               |
| ⏳ jalon 6 | `GET`  | `/api/revisions`  | Observations with several millésimes (value diff) — returns `RevisionDiff`                                  |
| ⏳ jalon 8 | `GET`  | `/api/sources`    | Metadata + attributions/licences (see §7) — returns `SourceInfo`                                            |
| ✖ jalon 9  | `GET`  | `/api/export.csv` | Export of the filtered view                                                                                 |

> There is also a ✅ `GET /api/health` liveness probe (used by the compose
> healthcheck), not part of the data contract.

`/api/series` response (example):

```json
{
  "query": {"source": "WID", "indicateur": "part_patrimoine", "groupe": "top1"},
  "unite": "adulte", "concept_patrimoine": "net", "unite_valeur": "%",
  "points": [{"annee": 2000, "valeur": 22.1}, {"annee": 2021, "valeur": 27.0}],
  "ruptures": [],
  "millesime_source": "WID 2026"
}
```

### 6.5 Frontend views

1. ✅ **Dashboard** (`/dashboard`) — top-share + Gini curves since 2000 in two
   stacked charts; filter bar from `/api/meta` (source/indicateur/groupe/concept +
   euros toggle); Concept picker + 422 "pick a Convention" fallback; 2018 break
   marker in the amber `rupture` token; per-figure traceability line; filter state
   in the URL. (jalon 4)
2. ⏳ **Source comparison** (`/comparison`) — routed **placeholder** today. Will
   overlay WID vs INSEE vs DGFiP for one dimensionless indicateur, each line
   Convention-labelled, with a "formes comparables, niveaux non comparables" banner.
   (jalon 5)
3. ⏳ **Sources & methodology** (`/sources`) — routed **placeholder** today. Will
   explain Conventions, the ISF/IFI break, survey limits, attributions/licences,
   millésimes and Révisions (the Révisions table lands in jalon 6, the narrative +
   licences in jalon 8).

---

## 7. Licences and attributions (to display in the app)

- **WID.world**: cite the work (Garbinti, Goupille-Lebret, Piketty) and
  WID.world; check the reuse/citation terms in force.
- **INSEE** and **DGFiP / data.gouv.fr**: reuse generally under the Open Licence
  (Etalab) — verify per dataset.
- Keep `source`, `millesime_source` and the extraction date visible for every
  displayed figure (traceability = a product requirement, not an option).

---

## 8. Secrets / configuration

- `WID_API_KEY_B64` (env) — known default: the public key from the official R
  package, base64 value `rYFByOB0ioaPATwHtllMI71zLOZSK0Ic5veQonJP`. **Sent
  verbatim** in `x-api-key`. May rotate / be rate-limited → cache it on the
  backend, do not call WID on every user request.
- `DGFIP_IFI_XLS_URL` (env) — URL of the IFI Excel (varies per millésime).

---

## 9. Jalon roadmap

This is the authoritative roadmap referenced by `TODO(jalon N)` markers in code.
The sequencing was refined in the **epic [#2](https://github.com/payouri/wealth-fr/issues/2)**
(lettered/decimal inserts avoid renumbering): a **frontend track** (4 → 5 → 6 → 8 →
9) that can proceed entirely against the jalon-3 fixture, and an independent
**data/ops track** (2 → 6.5 → 7) that only reconverges once real data replaces the
fixture. Each open jalon has (or gets) its own `ready-for-agent` issue.

| Jalon | Track | Status | Scope |
| ----- | ----- | ------ | ----- |
| **1** | scaffold | ✅ done | Repo & monorepo: §6.3 tree, scripts under `pipeline/`, requirements, README. |
| **2** | data/ops | ✅ done (#3) | **Parquet** output beside the cumulative CSV in the pipeline's write step. |
| **3** | backend | ✅ done (#1) | FastAPI + DuckDB (Parquet→CSV fallback); `/api/meta` + `/api/series` with the Convention guard rail and single-Millésime resolution (ADR 0002); contract tests. |
| **4** | frontend | ✅ done (#4) | Routing (`react-router-dom`) + URL state; design tokens wired; full filter bar from `/api/meta` incl. Concept picker, 422 fallback, euros toggle; two stacked charts (shares + Gini) via TanStack Query; 2018 amber rupture marker; loading/empty-200/422/error states; traceability line. |
| **5** | frontend | ⏳ pending (#5) | `GET /api/compare` (fans the jalon-3 resolver across sources, dimensionless only — ADR 0003) + comparison view with Convention-labelled legend and "niveaux non comparables" banner. |
| **6** | frontend | ⏳ pending (#6) | `GET /api/revisions` (returns `RevisionDiff` for Observations across >1 Millésime) + a Révisions table mounted in the Sources & méthodologie route. |
| **6.5** | data/ops | 🟡 partly done (#7) | **Live integration validation.** ✅ The real **WID** API now runs live in prod (key, format, batched fetch) and a real `WID 2026` Millésime exists. ⏳ Still pending: the **DGFiP** `.xlsx` parser against a real file (today DGFiP loads a curated CSV / pre-filled points), and explicit auth-failure → local-fallback coverage. Executes the ADR 0001 precondition / §10 risk. |
| **7** | data/ops | ✅ superseded by Coolify (#8) | Scheduled refresh of the Millésime. **Realised differently from the original plan:** instead of a GitHub Action committing the dataset to the repo, production refreshes via a **Coolify Scheduled Task** that `docker exec`s the always-on `pipeline-runner` (`docker-compose.production.yml`) running `--download --full` into a persistent `dataset` volume — the data is **not** versioned in the repo. The GitHub-Action variant (`.github/workflows/refresh-data.yml`) is a parked stub. Effective once live data exists (jalon 6.5). |
| **8** | frontend | ⏳ pending (#9) | Sources & méthodologie page (Conventions, ISF→IFI, survey limits, Millésimes/Révisions narrative) + `GET /api/sources` returning `SourceInfo` (url / convention / licence / attribution). Wraps the jalon-6 Révisions section. |
| **9** | frontend | ⏳ pending (#10) | Export: `GET /api/export.csv` (streams the filtered rows via the resolver) + client-side chart **PNG** export on Dashboard and Comparison. Share-a-view is already covered by jalon-4 URL state. |

All new backend endpoints **reuse the jalon-3 modules** (series resolver, ruptures
lookup, meta builder, dataset source resolver) — no parallel resolution paths.

---

## 10. Risks / open questions

- **Live validation — partly closed**: as of 2026-06 the **WID** API runs live in
  prod (real `WID 2026` Millésime). Still open under **jalon 6.5** (#7): the
  **DGFiP** `.xlsx` parser against a real file (DGFiP currently loads a curated CSV /
  pre-filled points) and explicit auth-failure → local-fallback handling.
- **DGFiP Excel parsing**: `download_file` retrieves the file but parsing depends
  on the real layout of the IFI sheet → write a dedicated parser once the file is
  in hand.
- **INSEE extension**: only a few points are curated; complete the HVP waves (and
  ideally the deciles) from Insee Références.
- **ISF ≤ 2017**: complete the ISF millésimes from the DGFiP archives to cover the
  whole early 2000s.
- **WID key rotation**: provide a clear error message + local-file fallback if
  auth fails.

---

## 11. Quick start

Full app (see [AGENTS.md](./AGENTS.md) for the canonical command list — pnpm is the
only package manager):

```bash
nvm use && pnpm bootstrap   # one-time: backend venv + deps, frontend deps
pnpm dev                    # backend (uvicorn :8000) + frontend (vite :5173)
# or the production-style stack (nginx SPA + /api proxy on 127.0.0.1:8080):
docker compose up --build
```

Pipeline only (run from `pipeline/`; outputs CSV + Parquet + dated `.xlsx`). The
pipeline is **not** on the compose `up` path — it is an opt-in `--profile data`
service (ADR 0001):

```bash
# via docker (keeps output files owned by you):
UID=$(id -u) GID=$(id -g) docker compose --profile data run --rm pipeline --download --full
# or directly, from pipeline/:
pip install -r requirements.txt
python build_dataset.py --download --full        # API retrieval (needs WID_API_KEY_B64)
python build_dataset.py --annee-min 2000         # local file fallback (no key)
```

---

## Appendix — gaps between this document and the built scaffold

This handoff describes the initial intent. The build diverges from it on a few
points decided with the user (see `README.md` and `CONTEXT.md`):

- **Repo**: GitHub `payouri/wealth-fr` (the local working directory is `eco_stats_viewer`).
- **Frontend**: pnpm · React 19 · TypeScript · Tailwind v4 · Vite 8 · **Recharts** (not visx) · TanStack Query · **react-router-dom** (URL state).
- **Backend**: FastAPI + **DuckDB** (reads the Parquet, falls back to CSV).
- **Quick start**: orchestrated from the repo root via pnpm (`pnpm dev`); the pipeline scripts live in `pipeline/` and also run as a `--profile data` compose service (see §11 and `AGENTS.md`).
- **Fix**: `build_dataset.py` reads `WID_API_KEY_B64` (not `WID_API_KEY`) to stay consistent with `netfetch.py` and §8.
