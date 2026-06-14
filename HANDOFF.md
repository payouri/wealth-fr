# Handoff — Webapp "Concentration du patrimoine en France depuis 2000"

> Handoff document for a coding agent. Goal: scaffold a complete web application
> from the work already done (the Python data pipeline). Everything below reflects
> the real state of the existing code and the methodological decisions already
> made; the "to build" sections are recommendations to adapt.

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

Two working, tested Python files (tested against simulated responses;
**not validated against the real servers**, because the development environment
had a restricted network).

### 2.1 `build_dataset.py` — orchestrator

Builds the harmonized, historised dataset, then writes it to CSV (cumulative) and
Excel (snapshot).

Key functions:

| Function | Role |
|---|---|
| `load_wid(path, …)` | Reads a local WID file (`WID_data_FR.csv`, `;` separator) → tidy |
| `_wid_rows_to_tidy(rows, …)` | Converts raw WID API rows → tidy |
| `load_insee(…)` | Pre-filled (curated) official INSEE points → tidy |
| `load_dgfip(path, …)` | ISF/IFI: external CSV if present, otherwise pre-filled points → tidy |
| `_stamp(rows, date, millesime)` | Adds the historisation fields |
| `deflate_levels(df, base_year)` | Converts levels (€) to constant euros (alters neither % nor Gini) |
| `harmonize(*frames, annee_min)` | Stacks the sources, filters the period, orders, validates the schema |
| `write_outputs(df, stem, append)` | Writes cumulative CSV + dated Excel, **detects revisions** |
| `main(argv)` | CLI |

CLI options: `--wid`, `--fiscal`, `--annee-min`, `--base-deflation`,
`--millesime-wid|insee|dgfip`, `--download`, `--full`, `--wid-api-key`,
`--dgfip-url`, `--no-append`.

### 2.2 `netfetch.py` — network layer

| Function | Role |
|---|---|
| `_http_get(url, …)` | Robust GET: timeout + exponential retries |
| `fetch_wid(api_key_b64, areas, codes, …)` | WID API call (restricted indicator list) |
| `fetch_wid_available(api_key_b64, areas, sixlets, …)` | Discovers the wealth percentiles available for a country |
| `fetch_wid_full(api_key_b64, areas, …)` | API-side "full file": all wealth percentiles, in batches of 40 |
| `download_file(url, dest, …)` | Direct download of a file (DGFiP Excel), no key |

---

## 3. Data model (the "tidy" schema)

One row = one Observation. This is the central **data contract** of the app.

| Column | Type | Description | Examples |
|---|---|---|---|
| `annee` | int | Year of the Observation | `2021` |
| `source` | str | Producer | `WID`, `INSEE`, `DGFiP` |
| `concept_patrimoine` | str | Wealth concept measured | `net`, `brut`, `total` (ISF), `immobilier` (IFI) |
| `unite` | str | Statistical unit | `adulte`, `menage`, `foyer_fiscal` |
| `groupe` | str | Sub-population | `ensemble`, `top10`, `top1`, `top0_1`, `bottom50`, `redevables`, … |
| `indicateur` | str | The measure | `part_patrimoine`, `gini`, `patrimoine_moyen`, `seuil`, `nb_foyers`, `impot_moyen` |
| `valeur` | float | Numeric value | `27.0` |
| `unite_valeur` | str | Unit of the value | `%`, `indice`, `euros`, `euros_constants_2021`, `effectif` |
| `euros_constants` | bool | Deflated value? | `true`/`false` |
| `date_extraction` | date | **[Historisation]** date of the pull | `2026-06-12` |
| `millesime_source` | str | **[Historisation]** version of the source file | `WID 2026`, `DGFiP 2024` |
| `notes` | str | Source variable, treatments, breaks | `WID API shweal_p99p100_992_j` |

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

| Source | Convention | Coverage | Access | Notes |
|---|---|---|---|---|
| **WID.world** | adulte / **net** wealth, equal-split | long annual series | **API** (key) or manual ZIP file | Reference for the top (combines fiscal + national accounts) |
| **INSEE** (HVP) | ménage / **brut** wealth | survey waves (1998, 2004, 2010, 2015, 2018, 2021, 2023) | curated points / FPR files / CASD | No dedicated API for the aggregates |
| **DGFiP** (ISF/IFI) | foyer fiscal | annual | Excel on impots.gouv.fr / data.gouv.fr | **2018 break** |

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

### 6.2 Recommended stack (to adapt)

- **Data**: keep the existing Python scripts as the ingestion layer. Pivot output
  in **Parquet** (in addition to CSV) for performance.
- **Backend**: **FastAPI** (Python) — reuses the pipeline and pandas directly.
  Storage: DuckDB or SQLite over the harmonized file (sufficient, the volume is
  small; a few thousand rows).
- **Frontend**: **React + TypeScript + Vite**, charting via **Recharts** or
  **visx**. Server state via **TanStack Query**.
- **Scheduled task**: a job (cron / GitHub Action) reruns the pipeline in
  `--download --full` mode and commits/publishes the new millésime.

### 6.3 Proposed tree

```
wealth-fr/
├── pipeline/                 # existing code, lightly reorganized
│   ├── build_dataset.py
│   ├── netfetch.py
│   ├── data/                 # WID_data_FR.csv, dgfip_isf_ifi.csv (raw sources)
│   └── out/                  # dataset_*.csv / .parquet / .xlsx
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI
│   │   ├── data.py           # parquet -> DuckDB loading, queries
│   │   └── models.py         # Pydantic schemas (see contract §6.4)
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── api/              # typed client
│   │   ├── components/       # charts, filters, break annotations
│   │   └── views/            # Dashboard, Comparison, Sources/Methodology
│   └── package.json
├── .github/workflows/refresh-data.yml
├── HANDOFF.md                # this document
└── README.md
```

### 6.4 API contract (proposal)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/meta` | Value lists: sources, indicateurs, groupes, conventions, millésimes |
| `GET` | `/api/series` | Filtered series. Query: `source, indicateur, groupe, concept, unite, annee_min, annee_max, euros_constants` |
| `GET` | `/api/compare` | Same indicateur/groupe across several sources |
| `GET` | `/api/revisions` | Observations with several millésimes (value diff) |
| `GET` | `/api/sources` | Metadata + attributions/licences (see §7) |
| `GET` | `/api/export.csv` | Export of the filtered view |

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

1. **Dashboard** — top-share + Gini curves since 2000; source/Convention toggle;
   2018 break marker.
2. **Source comparison** — overlay of WID vs INSEE vs DGFiP with an explicit
   reminder of the Conventions (unambiguous legend).
3. **Sources & methodology** — explains Conventions, the ISF/IFI break, survey
   limits, attributions/licences, millésimes and Révisions.

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

## 9. Scaffolding tasks (proposed jalons)

1. **Repo & monorepo**: create the §6.3 tree, move the two scripts into
   `pipeline/`, add `requirements.txt` (pandas, openpyxl, requests, fastapi,
   uvicorn, duckdb) and a `README`.
2. **Pivot step**: add a **Parquet** output to the pipeline in addition to CSV.
3. **Backend**: FastAPI + DuckDB loading of the parquet; implement `/api/meta`
   and `/api/series` first; tests against the §6.4 contract.
4. **Frontend**: Vite + React + TS; typed API client; Dashboard with a first
   curve (WID top 1%).
5. **Annotations & comparison**: 2018 break marker, multi-source comparison view
   with Convention guard rails.
6. **Revisions**: `/api/revisions` + a small diff view between millésimes.
7. **Refresh**: a GitHub Action running `--download --full`, publishing the new
   millésime (and detecting Révisions via the pipeline's output).
8. **Methodology & licences**: a dedicated page (§4, §5, §7).

---

## 10. Risks / open questions

- **No real validation done**: the WID/DGFiP calls were not tested against the
  servers (restricted dev network). Jalon 3 must begin with a real integration
  test (key, response format, rate-limit).
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

## 11. Quick start (current state of the pipeline)

```bash
pip install pandas openpyxl requests
# Option A — API (automatic retrieval)
python build_dataset.py --download --full
# Option B — local file (no key): drop data/WID_data_FR.csv then
python build_dataset.py --annee-min 2000
# Outputs: dataset_concentration_patrimoine_fr.csv (+ dated .xlsx)
```

---

## Appendix — gaps between this document and the built scaffold

This handoff describes the initial intent. The scaffold that was built diverges on
a few points decided with the user (see `README.md` and `CONTEXT.md`):

- **Repo root**: `eco_stats_viewer` (not `wealth-fr`).
- **Frontend**: pnpm · React · TypeScript · Tailwind v4 · Vite 8 · **Recharts** (not visx) · TanStack Query.
- **Backend**: FastAPI + **DuckDB** (reads the Parquet, falls back to CSV).
- **Quick start**: the scripts now live in `pipeline/`; run from that folder (see `README.md`).
- **Fix**: `build_dataset.py` reads `WID_API_KEY_B64` (not `WID_API_KEY`) to stay consistent with `netfetch.py` and §8.
