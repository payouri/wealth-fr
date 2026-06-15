// Typed API client. Requests go to /api/* and are proxied to FastAPI in dev
// (see vite.config.ts).
import type { AmbiguousConventionDetail, Meta, RevisionDiff, Series, SourceInfo } from "./types";

/** A non-2xx response. `detail` carries the parsed FastAPI body when present —
 *  notably the `ambiguous_convention` choices on a 422 (ADR 0002). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: unknown,
  ) {
    super(`API ${status}`);
    this.name = "ApiError";
  }

  /** The 422 "pick a Convention" payload, or null for any other failure. */
  get ambiguousConvention(): AmbiguousConventionDetail | null {
    const d = this.detail as { error?: string } | undefined;
    return this.status === 422 && d?.error === "ambiguous_convention"
      ? (this.detail as AmbiguousConventionDetail)
      : null;
  }
}

/** Build a `/api/...` URL, dropping unset (undefined / "") params so the backend
 *  applies its own defaults (and the Convention guard isn't forced). */
function buildUrl(path: string, params?: Record<string, string | number | boolean>): string {
  const entries = params
    ? Object.entries(params).filter(([, v]) => v !== undefined && v !== "")
    : [];
  const qs = entries.length
    ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString()}`
    : "";
  return `/api${path}${qs}`;
}

async function get<T>(
  path: string,
  params?: Record<string, string | number | boolean>,
): Promise<T> {
  const res = await fetch(buildUrl(path, params));
  if (!res.ok) {
    // FastAPI errors are JSON ({detail: ...}); fall back to status text otherwise.
    let detail: unknown;
    try {
      detail = (await res.json())?.detail;
    } catch {
      detail = res.statusText;
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  meta: () => get<Meta>("/meta"),
  series: (params: {
    source: string;
    indicateur: string;
    groupe: string;
    concept?: string; // pin one Convention; omit to let the backend resolve or 422 (ADR 0002)
    unite?: string; // derived from source server-side; optional
    annee_min?: number;
    annee_max?: number;
    euros_constants?: boolean;
    millesime?: string;
  }) => get<Series>("/series", params),

  /** One Series per source for the same indicateur/groupe; each keeps its own
   *  Convention (overlaid, never merged — jalon 5, ADR 0003). 422 on ambiguity. */
  compare: (params: { indicateur: string; groupe: string; sources: string[] }) =>
    get<Series[]>("/compare", {
      indicateur: params.indicateur,
      groupe: params.groupe,
      sources: params.sources.join(","),
    }),

  /** Observations a source revised across millésimes (jalon 6). */
  revisions: () => get<RevisionDiff[]>("/revisions"),

  /** Provenance + licence/attribution per source (jalon 8, HANDOFF §7). */
  sources: () => get<SourceInfo[]>("/sources"),

  /** A direct download link for the filtered tidy rows (jalon 9). Returns a URL
   *  (not a fetch) so the UI can hand it to an `<a download>` / navigation. */
  exportCsvUrl: (params: {
    source: string;
    indicateur: string;
    groupe: string;
    concept?: string;
    unite?: string;
    annee_min?: number;
    annee_max?: number;
    euros_constants?: boolean;
    millesime?: string;
  }) => buildUrl("/export.csv", params),
};
