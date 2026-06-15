// Comparison state lives in the URL too (jalon 5, sharing = copy the link):
// /comparison?indicateur=gini&groupe=ensemble&sources=WID,INSEE deep-links to
// that exact overlay. Mirrors useDashboardParams; sources travel as a CSV list.
import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

export interface ComparisonParams {
  /** Dimensionless only (part_patrimoine | gini) — ADR 0003. */
  indicateur: string;
  groupe: string;
  /** Sources to overlay; each keeps its own Convention. */
  sources: string[];
}

const DEFAULTS = {
  indicateur: "part_patrimoine",
  groupe: "top1",
  sources: ["WID", "INSEE", "DGFiP"],
};

const DEFAULT_SOURCES_CSV = DEFAULTS.sources.join(",");

export function useComparisonParams(): [
  ComparisonParams,
  (patch: Partial<ComparisonParams>) => void,
] {
  const [searchParams, setSearchParams] = useSearchParams();

  const params = useMemo<ComparisonParams>(() => {
    const sourcesRaw = searchParams.get("sources");
    return {
      indicateur: searchParams.get("indicateur") || DEFAULTS.indicateur,
      groupe: searchParams.get("groupe") || DEFAULTS.groupe,
      sources: sourcesRaw ? sourcesRaw.split(",").filter(Boolean) : [...DEFAULTS.sources],
    };
  }, [searchParams]);

  const update = useCallback(
    (patch: Partial<ComparisonParams>) => {
      const next = { ...params, ...patch };
      setSearchParams(
        (prev) => {
          const sp = new URLSearchParams(prev);
          if (next.indicateur === DEFAULTS.indicateur) sp.delete("indicateur");
          else sp.set("indicateur", next.indicateur);
          if (next.groupe === DEFAULTS.groupe) sp.delete("groupe");
          else sp.set("groupe", next.groupe);
          const sourcesCsv = next.sources.join(",");
          if (sourcesCsv === DEFAULT_SOURCES_CSV || sourcesCsv === "") sp.delete("sources");
          else sp.set("sources", sourcesCsv);
          return sp;
        },
        { replace: false },
      );
    },
    [params, setSearchParams],
  );

  return [params, update];
}
