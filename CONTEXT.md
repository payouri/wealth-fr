# Concentration du patrimoine en France

Glossary for a webapp that explores and visualizes the concentration of wealth in
France since 2000, harmonizing three public sources whose measurement conventions
are deliberately **not** interchangeable.

> Domain terms below put the tidy data contract into words. The contract itself is the code: the Pydantic models in [`backend/app/models.py`](./backend/app/models.py) and the tidy-column list in [`backend/app/data.py`](./backend/app/data.py), mirrored in [`frontend/src/api/types.ts`](./frontend/src/api/types.ts).

## Language

**Observation**:
One measured value for a single combination of year, source, concept, unité, groupe and indicateur. The atomic row of the dataset.
_Avoid_: record, data point, entry

**Source**:
The producer of an Observation — `WID`, `INSEE`, or `DGFiP`.
_Avoid_: provider, origin

**Concept de patrimoine** (`concept_patrimoine`):
Which wealth is measured — `net`, `brut`, `total` (ISF), or `immobilier` (IFI).
_Avoid_: wealth type, asset class

**Unité statistique** (`unité`):
The entity the value is counted over — `adulte`, `menage`, or `foyer_fiscal`.
_Avoid_: unit, level

**Convention**:
An (Unité + Concept) pair. The guard rail of the whole product: values may only be compared within the same Convention. A Source carries one Unité but possibly several Conventions (one per Concept it spans — see Relationships).
_Avoid_: methodology, basis

**Groupe**:
The sub-population a value describes — `ensemble`, `top10`, `top1`, `top0_1`, `bottom50`, `middle40`, `redevables`, …
_Avoid_: segment, bucket, cohort

**Indicateur**:
The measure itself — `part_patrimoine`, `gini`, `patrimoine_moyen`, `seuil`, `nb_foyers`, `impot_moyen`.
_Avoid_: metric, variable

**Millésime** (`millesime_source`):
The version/vintage of a Source file (e.g. `WID 2026`, `DGFiP 2024`).
_Avoid_: version, release, edition

**Extraction**:
A dated pull of data from a Source, stamped with `date_extraction`.
_Avoid_: import, fetch, snapshot

**Révision**:
Two Observations that share the same historisation key but differ in value and Millésime. Both are kept; never overwritten.
_Avoid_: update, correction, overwrite

**Rupture ISF→IFI**:
The 2018 series break: through 2017 the ISF taxed total wealth (`concept = total`); from 2018 the IFI taxes only real estate (`concept = immobilier`). Pre-2018 and post-2018 amounts are not comparable.
_Avoid_: transition, change

**Euros constants**:
A deflated level (€), produced in addition to the nominal value. Applies only to levels — never to shares (%) or Gini.
_Avoid_: real terms, adjusted

## Relationships

- A **Source** has exactly one **Unité**, but one *or more* **Concepts de patrimoine** — a new Concept begins at a **Rupture** (DGFiP carries `total` through 2017, then `immobilier` from 2018). So a Source can span more than one **Convention**; only the Unité is fixed per Source.
- An **Observation** belongs to one **Source** and carries one **Concept**, one **Unité**, one **Groupe**, one **Indicateur**
- A **Révision** links two **Observations** sharing a historisation key but differing in value and **Millésime**
- The historisation key is `annee, source, concept_patrimoine, unite, groupe, indicateur`

## Example dialogue

> **Dev:** "Can I plot WID's top-1% share next to INSEE's on the same axis?"
> **Domain expert:** "Only with a warning. WID is `adulte`/`net`, INSEE is `menage`/`brut` — different **Conventions**. The shapes are comparable as trends, but the levels are not the same quantity. The UI must label each line's Convention, never merge them silently."

> **Dev:** "WID changed the 2015 top-1% number between two **Millésimes** — which do I show?"
> **Domain expert:** "Both. That's a **Révision** — keep the old and new **Observations**, show the diff. We never overwrite."

## Flagged ambiguities

- "comparer les sources" means *overlay with explicit Convention labels*, not *aggregate into one series* — the Convention guard rail forbids the latter.
