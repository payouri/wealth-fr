# Cross-source comparison is restricted to dimensionless indicators

The multi-source comparison view (`/api/compare`, jalon 5) overlays Sources only
for **dimensionless** indicateurs — `part_patrimoine` (%) and `gini` (index) —
where a shared axis is honest. Level indicateurs measured in euros
(`patrimoine_moyen`, `seuil`, …) are **not offered** in comparison, because each
Source carries a different Unité (`adulte` / `menage` / `foyer_fiscal`) and a euro
amount per adult, per household, and per foyer fiscal are different quantities that
cannot share an axis even in shape.

## Context

CONTEXT.md's own example dialogue blesses overlaying top-share series across
Conventions *with a warning* — "the shapes are comparable as trends, but the levels
are not the same quantity… label each line's Convention, never merge them." That
reasoning holds for shares and Gini, which are unit-free. It breaks for euro levels:
a per-adult mean and a per-household mean differ by roughly the household size, so an
overlay would invite exactly the apples-to-oranges misread the Convention guard rail
exists to prevent.

## Decision

- Comparison overlays only `part_patrimoine` and `gini`, on one shared axis, with
  each line labelled by its Convention (Unité / Concept) and a banner reminding that
  shapes are comparable but levels are not.
- Euro-level indicateurs are excluded from the comparison view entirely (they remain
  available per-Source in the dashboard, never cross-Source).

## Consequences

- `/api/compare` only needs to fan the jalon-3 Series resolver across the requested
  Sources for a dimensionless indicateur; it never has to reconcile differing
  `unite_valeur` on one axis.
- A future reader who wonders "why can't I compare `patrimoine_moyen` across
  Sources?" finds the answer here: it is a deliberate guard-rail decision, not a
  missing feature. Revisit only if a defensible normalisation across Unités is
  introduced.
