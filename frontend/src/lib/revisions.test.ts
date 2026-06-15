import { describe, expect, it } from "vitest";
import type { RevisionDiff } from "@/api/types";
import { orderedMillesimes, revisionDelta } from "./revisions";

const seeded: RevisionDiff = {
  annee: 2015,
  source: "WID",
  concept_patrimoine: "net",
  unite: "adulte",
  groupe: "top1",
  indicateur: "part_patrimoine",
  // Deliberately newest-first to prove ordering doesn't depend on input order.
  valeurs: [
    { millesime_source: "WID 2026", valeur: 26.5, date_extraction: "2026-06-12" },
    { millesime_source: "WID 2024", valeur: 26.0, date_extraction: "2024-06-01" },
  ],
};

describe("orderedMillesimes", () => {
  it("orders the competing millésimes oldest → newest by extraction date", () => {
    expect(orderedMillesimes(seeded).map((v) => v.millesime_source)).toEqual([
      "WID 2024",
      "WID 2026",
    ]);
  });
});

describe("revisionDelta", () => {
  it("diffs the earliest value against the latest, keeping both", () => {
    const d = revisionDelta(seeded);
    expect(d?.from.valeur).toBe(26.0);
    expect(d?.to.valeur).toBe(26.5);
    expect(d?.delta).toBeCloseTo(0.5);
  });

  it("returns null when there is only one millésime (nothing to diff)", () => {
    expect(revisionDelta({ ...seeded, valeurs: [seeded.valeurs[0]] })).toBeNull();
  });
});
