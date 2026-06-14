// Typed API client. Requests go to /api/* and are proxied to FastAPI in dev
// (see vite.config.ts).
import type { Meta, Series } from "./types";

async function get<T>(
  path: string,
  params?: Record<string, string | number | boolean>,
): Promise<T> {
  const qs = params
    ? `?${new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString()}`
    : "";
  const res = await fetch(`/api${path}${qs}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  meta: () => get<Meta>("/meta"),
  series: (params: {
    source: string;
    indicateur: string;
    groupe: string;
    concept?: string;
    unite?: string;
    annee_min?: number;
    annee_max?: number;
    euros_constants?: boolean;
  }) => get<Series>("/series", params),
  // TODO: compare, revisions, sources, export.csv
};
