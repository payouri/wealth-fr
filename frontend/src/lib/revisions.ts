// Révisions (jalon 6): present an Observation revised across millésimes. The API
// keeps every competing millésime (append-only historisation); here we order them
// oldest → newest and compute the net change, without ever dropping one.
import type { RevisionDiff } from "@/api/types";

export interface RevisionRow {
  millesime_source: string;
  valeur: number;
  date_extraction: string;
}

/** Millésimes oldest → newest by extraction date (the order a révision happened). */
export function orderedMillesimes(rev: RevisionDiff): RevisionRow[] {
  return [...rev.valeurs].sort((a, b) => a.date_extraction.localeCompare(b.date_extraction));
}

/** The net révision: earliest value → latest value, and their signed delta.
 *  Returns null when there is nothing to diff (fewer than two millésimes). */
export function revisionDelta(
  rev: RevisionDiff,
): { from: RevisionRow; to: RevisionRow; delta: number } | null {
  const ordered = orderedMillesimes(rev);
  if (ordered.length < 2) return null;
  const from = ordered[0];
  const to = ordered[ordered.length - 1];
  return { from, to, delta: to.valeur - from.valeur };
}
