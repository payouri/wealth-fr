// Domain vocabulary for the UI: French display labels for the data-contract
// identifiers (which stay verbatim everywhere — see AGENTS.md "Conventions"),
// plus the chart encoding (colour + dash) and value formatting.
//
// Encoding rule (DESIGN.md §2): meaning never rests on hue alone. Every series
// pairs a colour with a dash pattern and a direct end-of-line label, so it
// survives colourblindness and greyscale.
import type { Concept, Meta, Source } from "@/api/types";

export const SOURCE_LABEL: Record<string, string> = {
  WID: "WID.world",
  INSEE: "INSEE",
  DGFiP: "DGFiP",
};

/** What each source measures, surfaced next to its name so the Convention is
 *  never implicit (Principle 1: "The Convention is the contract"). */
export const SOURCE_CONVENTION: Record<string, string> = {
  WID: "adultes · patrimoine net",
  INSEE: "ménages · brut/net (et hors reste)",
  DGFiP: "foyers fiscaux · ISF/IFI",
};

export const CONCEPT_LABEL: Record<string, string> = {
  net: "net",
  brut: "brut",
  brut_hors_reste: "brut hors reste",
  net_hors_reste: "net hors reste",
  total: "total (ISF)",
  immobilier: "immobilier (IFI)",
};

export const UNITE_LABEL: Record<string, string> = {
  adulte: "par adulte",
  menage: "par ménage",
  foyer_fiscal: "par foyer fiscal",
};

export const GROUPE_LABEL: Record<string, string> = {
  ensemble: "Ensemble",
  top10: "Top 10 %",
  top5: "Top 5 %",
  top1: "Top 1 %",
  top0_1: "Top 0,1 %",
  top50: "Top 50 %",
  bottom50: "Bottom 50 %",
  middle40: "Milieu 40 %",
  mediane: "Médiane",
  redevables: "Redevables",
  patrimoine_sup_10M: "Patrimoine > 10 M€",
};

// Standalone groups (neither a concentration fraction nor part of a numbered
// family). Offered ungrouped at the top of a curated select, in this order.
const STANDALONE_GROUPES = ["redevables", "patrimoine_sup_10M"] as const;

// The DGFiP numbered families, namespaced by the variable ranked on (CONTEXT.md).
// `decile_<var>_<n>` and `tranche_marginale_<n>` carry an index that is a data
// fact; the label is composed from it (and, for tranches, from `meta.tranche_taux`).
const DECILE_VAR_LABEL: Record<string, string> = {
  patrimoine: "patrimoine",
  rfr: "revenu",
};

// Family headers (French, editorial — issue #15) for the grouped Groupe select.
const FAMILY_HEADER = {
  decile_patrimoine: "Patrimoine",
  decile_rfr: "Revenu fiscal (RFR)",
  tranche_marginale: "Tranche marginale d'imposition",
} as const;

const DECILE_RE = /^decile_(patrimoine|rfr)_(\d+)$/;
const TRANCHE_RE = /^tranche_marginale_(\d+)$/;

const rateFmt = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });

/** French display label for a groupe code. Static fractions are looked up; the
 *  DGFiP numbered families are composed from the index (and, for tranches, the
 *  marginal rate threaded via `meta.tranche_taux`). A non-curated code (e.g. a raw
 *  WID percentile bracket reached from a hand-typed URL) falls back to itself, so
 *  deep links keep resolving (issue #15). */
export function groupeLabel(g: string, meta?: Pick<Meta, "tranche_taux">): string {
  const decile = DECILE_RE.exec(g);
  if (decile) {
    const variable = DECILE_VAR_LABEL[decile[1]];
    const n = Number(decile[2]);
    // Annotation keys off the FIXED index, never the position in the list: a
    // missing 10th décile leaves the 9th simply unannotated, never mislabelled.
    const extreme = n === 1 ? " (le plus faible)" : n === 10 ? " (le plus élevé)" : "";
    return `Décile ${n} de ${variable}${extreme}`;
  }
  const tranche = TRANCHE_RE.exec(g);
  if (tranche) {
    const taux = meta?.tranche_taux?.[g];
    if (taux != null) return `Tranche à ${rateFmt.format(taux)} %`;
    return GROUPE_LABEL[g] ?? g; // no rate known → raw fallback (deep-link safe)
  }
  return GROUPE_LABEL[g] ?? g;
}

// Canonical ordered concentration fractions offered by the Groupe selects, nested
// from the whole population down to the very top (issue #15). `top5` (added with
// INSEE's ingested top5 share, #14) sits between top10 and top1. The ~290 fine WID
// percentile brackets stay in the data and in /api/meta, but are never OFFERED.
export const CONCENTRATION_GROUPES = [
  "ensemble",
  "bottom50",
  "middle40",
  "top50",
  "top10",
  "top5",
  "top1",
  "top0_1",
] as const;

export interface GroupeOption {
  value: string;
  label: string;
}

/** One block of options in a curated Groupe select. `header` null → ungrouped
 *  (standalone or the concentration family); otherwise a screen-reader-announced
 *  family header (shadcn SelectGroup/SelectLabel). */
export interface GroupeOptionGroup {
  header: string | null;
  options: GroupeOption[];
}

/** The ordered, grouped, human-readable option model a non-share Groupe select
 *  renders — curation is presentation-only (issue #15): /api/meta still returns the
 *  full groupes/availability, and any underlying figure stays reachable by URL.
 *
 *  Standalone groups (`redevables`, `patrimoine_sup_10M`) come first, ungrouped.
 *  Concentration fractions are the canonical set ∩ what this (source, indicateur)
 *  measures, dropping the raw percentile lattice. The DGFiP numbered families are
 *  kept in full, numerically sorted, under a family header each.
 *
 *  `active` is the currently-selected groupe. The curation deliberately drops the
 *  WID percentile lattice, but `validComboForSource` can snap a non-share groupe to
 *  a lattice code (the source's first available groupe) — or a deep link may hold
 *  one. So when `active` is set but not among the curated options, it is appended as
 *  an ungrouped fallback (labelled via `groupeLabel`), so the trigger never renders
 *  blank and the code the reader actually has stays visible and re-selectable. */
export function groupeOptions(
  meta: Meta,
  source: string,
  indicateur: string,
  active?: string,
): GroupeOptionGroup[] {
  const available = new Set(meta.availability?.[source]?.[indicateur] ?? []);
  const groups: GroupeOptionGroup[] = [];

  const standalone = STANDALONE_GROUPES.filter((g) => available.has(g));
  if (standalone.length > 0) {
    groups.push({
      header: null,
      options: standalone.map((g) => ({ value: g, label: groupeLabel(g, meta) })),
    });
  }

  const concentration = CONCENTRATION_GROUPES.filter((g) => available.has(g));
  if (concentration.length > 0) {
    groups.push({
      header: null,
      options: concentration.map((g) => ({ value: g, label: groupeLabel(g, meta) })),
    });
  }

  // DGFiP numbered families, numerically sorted by their index (1, 2, …10 — not the
  // lexical 1, 10, 2), under one family header each, in the canonical family order.
  for (const family of ["decile_patrimoine", "decile_rfr", "tranche_marginale"] as const) {
    const members = [...available]
      .filter((g) => g.startsWith(`${family}_`))
      .map((g) => ({ g, n: Number(g.slice(g.lastIndexOf("_") + 1)) }))
      .filter((m) => Number.isFinite(m.n))
      .sort((a, b) => a.n - b.n);
    if (members.length > 0) {
      groups.push({
        header: FAMILY_HEADER[family],
        options: members.map(({ g }) => ({ value: g, label: groupeLabel(g, meta) })),
      });
    }
  }

  // Belt-and-suspenders: keep the active selection offered. If a non-curated code
  // (e.g. a WID lattice bracket snapped in by `validComboForSource`, or a deep link)
  // is selected but absent from every block above, append it ungrouped so the
  // trigger stays legible and the value stays re-selectable (issue #15).
  if (active && !groups.some((grp) => grp.options.some((o) => o.value === active))) {
    groups.push({ header: null, options: [{ value: active, label: groupeLabel(active, meta) }] });
  }

  return groups;
}

// The dashboard's headline: the three top shares, plotted together on one axis.
export const SHARE_GROUPES = ["top10", "top5", "top1", "top0_1"] as const;

// Only dimensionless indicateurs may be compared across Sources: their shapes are
// comparable even when the underlying Unités are not (ADR 0003). Euro levels are
// excluded — the comparison view never offers them.
export const COMPARABLE_INDICATEURS = ["part_patrimoine", "gini"] as const;

// Stable groupe -> (colour, dash) on the single-source shares chart. Three
// distinct Okabe-Ito hues; the dash pattern is the redundant, hue-free cue.
export const GROUPE_ENCODING: Record<string, { color: string; dash: string }> = {
  top10: { color: "var(--color-chart-1)", dash: "0" }, // solid
  top5: { color: "var(--color-chart-5)", dash: "4 3" }, // short-dash (INSEE)
  top1: { color: "var(--color-chart-2)", dash: "7 4" }, // dashed
  top0_1: { color: "var(--color-chart-4)", dash: "2 4" }, // dotted
};

// One stable hue per source, for single-series charts (Gini, levels) and the
// future cross-source comparison view (DESIGN.md §2).
export const SOURCE_ENCODING: Record<string, { color: string; dash: string }> = {
  WID: { color: "var(--color-chart-1)", dash: "0" },
  INSEE: { color: "var(--color-chart-2)", dash: "7 4" },
  DGFiP: { color: "var(--color-chart-3)", dash: "2 4" },
};

export interface IndicateurMeta {
  label: string;
  /** Distributional shares get the 3-line headline; everything else is one line. */
  isShare: boolean;
  /** Deflation applies to levels only — the euros toggle is inert otherwise. */
  isLevel: boolean;
  /** y-axis caption. */
  axis: string;
}

export const INDICATEUR_META: Record<string, IndicateurMeta> = {
  part_patrimoine: {
    label: "Part du patrimoine",
    isShare: true,
    isLevel: false,
    axis: "% du patrimoine total",
  },
  gini: { label: "Indice de Gini", isShare: false, isLevel: false, axis: "indice (0–1)" },
  patrimoine_moyen: { label: "Patrimoine moyen", isShare: false, isLevel: true, axis: "euros" },
  seuil: { label: "Seuil d'entrée", isShare: false, isLevel: true, axis: "euros" },
  nb_foyers: { label: "Nombre de foyers", isShare: false, isLevel: false, axis: "foyers" },
  impot_moyen: { label: "Impôt moyen", isShare: false, isLevel: true, axis: "euros" },
};

export function indicateurMeta(ind: string): IndicateurMeta {
  return INDICATEUR_META[ind] ?? { label: ind, isShare: false, isLevel: false, axis: "" };
}

type Availability = Record<string, Record<string, string[]>>;

/** Snap an (indicateur, groupe) pair to one the source actually measures
 *  (`meta.availability`). Sources measure disjoint figures, so switching source —
 *  or landing on a hand-typed URL — can leave an indicateur/groupe the new source
 *  never measured, which silently empties the chart. Keep the current pick when
 *  it is valid; otherwise fall back to the source's first available indicateur and
 *  (for non-share indicateurs) its first groupe. Share indicateurs overlay all
 *  fractions, so their groupe is a focus that may stay empty ("" = no focus). */
export function validComboForSource(
  availability: Availability | undefined,
  source: string,
  indicateur: string,
  groupe: string,
): { indicateur: string; groupe: string } {
  const byIndicateur = availability?.[source] ?? {};
  const indicateurs = Object.keys(byIndicateur);
  const ind = indicateurs.includes(indicateur) ? indicateur : (indicateurs[0] ?? indicateur);
  const groupes = byIndicateur[ind] ?? [];
  if (indicateurMeta(ind).isShare) {
    return { indicateur: ind, groupe: groupe && groupes.includes(groupe) ? groupe : "" };
  }
  return {
    indicateur: ind,
    groupe: groupe && groupes.includes(groupe) ? groupe : (groupes[0] ?? ""),
  };
}

// --- value formatting (fr-FR, tabular-friendly) --------------------------------

const nf = (max: number, min = 0) =>
  new Intl.NumberFormat("fr-FR", { minimumFractionDigits: min, maximumFractionDigits: max });

/** Format a value for axis ticks, tooltips and inline figures, by its unit. */
export function formatValue(value: number, uniteValeur: string): string {
  if (uniteValeur === "%") return `${nf(1).format(value)} %`;
  if (uniteValeur === "indice") return nf(3, 3).format(value);
  if (uniteValeur === "effectif" || uniteValeur === "foyers")
    return nf(0).format(Math.round(value));
  if (uniteValeur.startsWith("euros")) return `${nf(0).format(Math.round(value))} €`;
  return nf(2).format(value);
}

/** Compact axis tick: shares stay plain, large counts/euros get a k/M suffix. */
export function formatTick(value: number, uniteValeur: string): string {
  if (uniteValeur === "%") return `${nf(0).format(value)}`;
  if (uniteValeur === "indice") return nf(2, 1).format(value);
  if (Math.abs(value) >= 1_000_000) return `${nf(1).format(value / 1_000_000)} M`;
  if (Math.abs(value) >= 1_000) return `${nf(0).format(value / 1_000)} k`;
  return nf(0).format(value);
}

/** The Convention label carried on every plotted line and traceability row. */
export function conventionLabel(
  source: Source | string,
  unite: string,
  concept: Concept | string,
): string {
  const u = UNITE_LABEL[unite] ?? unite;
  const c = CONCEPT_LABEL[concept] ?? concept;
  return `${SOURCE_LABEL[source] ?? source} · ${u} · ${c}`;
}
