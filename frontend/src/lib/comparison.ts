// Cross-source comparison (jalon 5, ADR 0003): turn the list of per-source
// Series from /api/compare into chart lines + a Convention legend. Each source
// keeps its own (colour, dash, Convention) so overlaid Sources are never read as
// merged — the guard rail, made visible.
import type { Series } from "@/api/types";
import type { ChartSeries } from "@/components/SeriesChart";
import { conventionLabel, SOURCE_ENCODING, SOURCE_LABEL } from "@/lib/domain";

export interface ComparisonLine extends ChartSeries {
  /** The source this line belongs to (its stable key + colour). */
  source: string;
  /** "WID.world · par adulte · net" — the Convention, shown in the legend. */
  convention: string;
  /** False when the source returned no Observations for this indicateur/groupe. */
  hasData: boolean;
}

const FALLBACK = { color: "var(--color-chart-4)", dash: "0" };

/** One line per Source, in the order the API returned them. Sources with no
 *  Observations are kept (so the legend can say "no data") but flagged. */
export function buildComparisonLines(seriesList: Series[]): ComparisonLine[] {
  return seriesList.map((s) => {
    const source = String(s.query.source ?? "");
    const enc = SOURCE_ENCODING[source] ?? FALLBACK;
    return {
      key: source,
      label: SOURCE_LABEL[source] ?? source,
      points: s.points,
      color: enc.color,
      dash: enc.dash,
      source,
      convention: conventionLabel(source, s.unite, s.concept_patrimoine),
      hasData: s.points.length > 0,
    };
  });
}
