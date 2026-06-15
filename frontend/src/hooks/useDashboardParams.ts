// The dashboard's state lives in the URL: the query string IS the shareable
// view (copy URL = share, Back button works). Issue #4 acceptance:
// /dashboard?source=WID&groupe=top1&concept=net deep-links to that exact view.
import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

export interface DashboardParams {
  source: string;
  indicateur: string;
  /** Focused groupe: highlights one line on the shares chart, or selects the
   *  single groupe for non-share indicateurs. "" = no focus / all three. */
  groupe: string;
  /** Pinned Convention; "" until chosen (or resolved by the backend). */
  concept: string;
  /** Constant euros toggle; inert (and forced off) unless the indicateur is a level. */
  euros: boolean;
}

const DEFAULTS: DashboardParams = {
  source: "WID",
  indicateur: "part_patrimoine",
  groupe: "",
  concept: "",
  euros: false,
};

export type UpdateParams = (patch: Partial<DashboardParams>, opts?: { replace?: boolean }) => void;

export function useDashboardParams(): [DashboardParams, UpdateParams] {
  const [searchParams, setSearchParams] = useSearchParams();

  const params = useMemo<DashboardParams>(
    () => ({
      source: searchParams.get("source") || DEFAULTS.source,
      indicateur: searchParams.get("indicateur") || DEFAULTS.indicateur,
      groupe: searchParams.get("groupe") || DEFAULTS.groupe,
      concept: searchParams.get("concept") || DEFAULTS.concept,
      euros: searchParams.get("euros") === "1",
    }),
    [searchParams],
  );

  const update = useCallback<UpdateParams>(
    (patch, opts) => {
      const next = { ...params, ...patch };
      // A Convention from one source is meaningless for another — drop it when
      // the source changes so we never carry a stale concept across sources.
      if (patch.source && patch.source !== params.source && patch.concept === undefined) {
        next.concept = "";
      }
      setSearchParams(
        (prev) => {
          const sp = new URLSearchParams(prev);
          for (const [key, value] of Object.entries(next) as [keyof DashboardParams, unknown][]) {
            const def = DEFAULTS[key];
            const isDefault = key === "euros" ? value === def : (value || "") === def;
            if (isDefault) sp.delete(key);
            else sp.set(key, key === "euros" ? "1" : String(value));
          }
          return sp;
        },
        { replace: opts?.replace ?? false },
      );
    },
    [params, setSearchParams],
  );

  return [params, update];
}
