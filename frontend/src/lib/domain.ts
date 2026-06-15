// Domain vocabulary for the UI: French display labels for the data-contract
// identifiers (which stay verbatim everywhere — see AGENTS.md "Conventions"),
// plus the chart encoding (colour + dash) and value formatting.
//
// Encoding rule (DESIGN.md §2): meaning never rests on hue alone. Every series
// pairs a colour with a dash pattern and a direct end-of-line label, so it
// survives colourblindness and greyscale.
import type { Concept, Source } from "@/api/types";

export const SOURCE_LABEL: Record<string, string> = {
  WID: "WID.world",
  INSEE: "INSEE",
  DGFiP: "DGFiP",
};

/** What each source measures, surfaced next to its name so the Convention is
 *  never implicit (Principle 1: "The Convention is the contract"). */
export const SOURCE_CONVENTION: Record<string, string> = {
  WID: "adultes · patrimoine net",
  INSEE: "ménages · patrimoine brut",
  DGFiP: "foyers fiscaux · ISF/IFI",
};

export const CONCEPT_LABEL: Record<string, string> = {
  net: "net",
  brut: "brut",
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
  top1: "Top 1 %",
  top0_1: "Top 0,1 %",
  top50: "Top 50 %",
  bottom50: "Bottom 50 %",
  middle40: "Milieu 40 %",
  redevables: "Redevables",
  patrimoine_sup_10M: "Patrimoine > 10 M€",
};

export function groupeLabel(g: string): string {
  return GROUPE_LABEL[g] ?? g;
}

// The dashboard's headline: the three top shares, plotted together on one axis.
export const SHARE_GROUPES = ["top10", "top1", "top0_1"] as const;

// Only dimensionless indicateurs may be compared across Sources: their shapes are
// comparable even when the underlying Unités are not (ADR 0003). Euro levels are
// excluded — the comparison view never offers them.
export const COMPARABLE_INDICATEURS = ["part_patrimoine", "gini"] as const;

// Stable groupe -> (colour, dash) on the single-source shares chart. Three
// distinct Okabe-Ito hues; the dash pattern is the redundant, hue-free cue.
export const GROUPE_ENCODING: Record<string, { color: string; dash: string }> = {
  top10: { color: "var(--color-chart-1)", dash: "0" }, // solid
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
