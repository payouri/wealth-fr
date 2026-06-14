# AGENTS.md

Operating rules for coding agents working in this repo. This file is **rules of
engagement + commands + how to verify your work** — it is deliberately thin and
defers to the docs below for substance.

## Orientation

A webapp that explores and compares harmonized **wealth-concentration** series
for France since 2000, across three public sources (WID, INSEE, DGFiP) whose
measurement **Conventions are not interchangeable**. Today it is a structure-only
scaffold: the Python pipeline is real code; the backend and frontend are typed
stubs with `TODO(jalon N)` markers.

**Read these before changing anything — do not duplicate their content here:**

| Doc | What it is | When you need it |
|---|---|---|
| [HANDOFF.md](./HANDOFF.md) | The spec: intent, data schema (§3), API contract (§6.4), the **jalon roadmap (§9)**, risks (§10) | Implementing any `TODO(jalon N)` — N is defined in §9 |
| [CONTEXT.md](./CONTEXT.md) | Domain glossary (Observation, Convention, Révision, Rupture ISF→IFI…) | Any time a domain term's meaning matters |
| [README.md](./README.md) | Human-facing overview + quick start | Onboarding context |
| [docs/adr/](./docs/adr/) | Architecture decisions and *why* | Before reversing a structural choice |
| [PRODUCT.md](./PRODUCT.md) | Design context: register, users, brand personality, anti-references, design principles | Building or changing any UI |
| [DESIGN.md](./DESIGN.md) | Visual system: color, typography, components (seed until real tokens land) | Styling any frontend surface |

### Design Context

This is a **product**-register surface for the **informed general public**, with an
**editorial / explanatory** personality (data journalism, not a dashboard). Five
principles guide all UI work (full text in [PRODUCT.md](./PRODUCT.md)):

1. **The Convention is the contract** — overlay series, never merge; every line declares its unité/concept.
2. **Traceability is a feature, not a footnote** — source, millésime, extraction date visible per figure.
3. **Explain the break, don't smooth it** — annotate the 2018 ISF→IFI rupture and révisions.
4. **Lead the reader, respect the data** — progressive disclosure; accessible never means dumbed down.
5. **Honest charts only** — no axis tricks, no decoration over integrity, no color-only meaning.

Accessibility target: **WCAG 2.1 AA + colorblind-safe** (never color-only encoding; respect reduced-motion).

**Component sourcing: shadcn/ui first.** Prefer installing a **shadcn/ui** primitive
and restyling it to the DESIGN.md tokens before hand-rolling a custom one. It fits the
stack (React 19 + Tailwind v4 + Radix) and supplies accessible, state-complete
components that serve the WCAG AA goal. Hand-roll only when no shadcn equivalent
exists or restyling costs more than building from scratch (chart surface, Convention
legend, traceability line are custom by nature). Never ship a shadcn component in its
default skin: bend it to the tokens (warm paper, slate-teal accent, 8px radius, no
pills, tabs as an underline). See [DESIGN.md](./DESIGN.md) "The Borrowed Primitive Rule".

## Non-negotiables

These encode the product's meaning. Breaking one produces output that *looks*
correct and is silently wrong. They span every layer (pipeline → backend → UI).

1. **Convention guard rail.** `unite` + `concept_patrimoine` qualify every value.
   **Never** aggregate or compare across Conventions (e.g. WID `adulte`/`net` vs
   INSEE `menage`/`brut`). Expose them as first-level filters; echo them in every
   API response; label every plotted line. ("comparer les sources" = overlay with
   explicit Convention labels, **not** merge into one series.)
2. **Append-only historisation.** Sources revise past years retroactively.
   Observations are **never** overwritten — both millésimes of a revised value
   coexist (a **Révision**). Key: `annee, source, concept_patrimoine, unite,
   groupe, indicateur` (`HIST_KEYS`).
3. **Deflation only on levels.** `euros_constants` rows are added *alongside*
   nominal ones. **Never** deflate shares (%) or Gini.
4. **Traceability is a feature.** `source`, `millesime_source`, `date_extraction`
   stay visible for every displayed figure.

## Commands

All orchestration runs from the repo root via pnpm (the **only** package manager —
never `npm`/`yarn`; the pnpm version is pinned in `package.json`).

```bash
nvm use          # Node 24 (pinned in .nvmrc; matches CI + the frontend Dockerfile)
pnpm bootstrap   # one-time: create backend/.venv + install backend & dev deps; install frontend deps
pnpm dev         # run backend (uvicorn :8000) + frontend (vite :5173) together
pnpm api         # backend only
pnpm web         # frontend only
```

Production-style stack (nginx serves the built SPA, reverse-proxies `/api` to the
backend; single host entry on `127.0.0.1:8080`):

```bash
docker compose up --build                          # serve the app
docker compose --profile data run --rm pipeline --download --full   # (re)generate the dataset
```

> The pipeline is **not** on the `docker compose up` path by design — it is an
> opt-in `--profile data` service. See [ADR 0001](./docs/adr/0001-pipeline-off-compose-startup-path.md).

Per-component gates (the `<tool>` for Python lives in `backend/.venv/bin/`):

| Component | Lint | Format check | Types | Tests |
|---|---|---|---|---|
| Python (`pipeline/`, `backend/`) | `ruff check .` | `ruff format --check .` | `mypy` | `cd backend && pytest` |
| Frontend (`frontend/`) | `pnpm lint` | (Biome, same as lint) | `pnpm typecheck` | `pnpm test` |

Auto-fix formatting: `ruff format .` (Python) / `pnpm format` (frontend).

## Conventions

- **Language.** Prose is **English**. The French **domain identifiers are the data
  contract** and stay verbatim everywhere — `concept_patrimoine`, `unite`,
  `groupe`, `indicateur`, `millesime_source`, `valeur`, `euros_constants`, their
  values (`net`, `brut`, `menage`, `foyer_fiscal`, `redevables`, `top1`…), and the
  words `jalon` / `millésime`. Renaming any of these is a breaking migration across
  pipeline + backend + frontend, not a doc edit.
- **The contract has two mirrors that must agree:** [backend/app/models.py](./backend/app/models.py)
  (Pydantic) ↔ [frontend/src/api/types.ts](./frontend/src/api/types.ts) (TS).
  Change one → change the other; both trace to HANDOFF.md §6.4.
- **Toolchain:** Python = ruff (lint + format) + mypy, target `py312` (config in
  [pyproject.toml](./pyproject.toml)). Frontend = Biome (lint + format) + strict
  `tsc` + Vitest (config in `frontend/biome.json`). Node is pinned to **24** in
  `.nvmrc` — the single source of truth that CI and the frontend Dockerfile track.

## Traps

Things the code won't tell you, that have already bitten this project:

- **WID API key is sent verbatim.** `WID_API_KEY_B64` is base64 already; it goes
  into `x-api-key` **without re-encoding**. Re-encoding breaks auth. It is a public
  key that may rotate / be rate-limited → cache server-side, never call WID per
  user request. (HANDOFF.md §8)
- **Network was never tested against live servers** (restricted dev network). The
  pipeline was validated only on simulated responses and falls back to a local
  file. **jalon 3 must begin with a real WID/DGFiP integration test.** (HANDOFF.md §10)
- **Parquet preferred, CSV fallback.** The backend reads Parquet if present, else
  the cumulative CSV. The Parquet output is still TODO (**jalon 2**).
- **Stubs are intentional.** `raise NotImplementedError` / `TODO(jalon N)` are not
  bugs. Resolve N against HANDOFF.md §9 *before* implementing; don't "fix" a stub
  blind.
- **Don't translate the schema identifiers** (see Conventions) — they are French
  on purpose.

## Definition of done

Before claiming a task complete, the relevant gates must pass:

```bash
# Python (from repo root, using the venv)
backend/.venv/bin/ruff check .
backend/.venv/bin/ruff format --check .
backend/.venv/bin/mypy
cd backend && .venv/bin/pytest

# Frontend (from frontend/)
pnpm lint && pnpm typecheck && pnpm test
```

CI ([.github/workflows/ci.yml](./.github/workflows/ci.yml)) runs exactly these
gates plus `docker compose build` on every push/PR — a green CI run is the same
bar as a passing local DoD. When you un-skip a contract test (the
`@pytest.mark.skip` markers tied to jalons), do it as the matching endpoint lands.

## Agent skills

### Issue tracker

Issues and PRDs live as GitHub issues in `payouri/wealth-fr` (via the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles use their default names, plus an `epic` grouping label. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Frontend design

All frontend design work goes through the `impeccable` skill (`/impeccable <command>`),
which reads [PRODUCT.md](./PRODUCT.md) (strategy: register, users, principles) and
[DESIGN.md](./DESIGN.md) (visual system: tokens, type, components) before touching any
UI. Use `/impeccable craft <view>` to build a surface, `critique` / `audit` to review
one. The design tokens are normative; honour the "Design Context" block above.
