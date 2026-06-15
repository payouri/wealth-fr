import { describe, expect, it } from "vitest";
import type { Series } from "@/api/types";
import { buildComparisonLines } from "./comparison";

function series(over: Partial<Series> & { source: string }): Series {
  const { source, ...rest } = over;
  return {
    query: { source },
    unite: "adulte",
    concept_patrimoine: "net",
    unite_valeur: "%",
    points: [{ annee: 2015, valeur: 26.5 }],
    ruptures: [],
    millesime_source: "WID 2026",
    date_extraction: "2026-06-12",
    ...rest,
  };
}

describe("buildComparisonLines", () => {
  it("gives each source its own colour, dash and Convention label", () => {
    const lines = buildComparisonLines([
      series({ source: "WID", unite: "adulte", concept_patrimoine: "net" }),
      series({ source: "INSEE", unite: "menage", concept_patrimoine: "brut" }),
    ]);
    const wid = lines.find((l) => l.source === "WID");
    const insee = lines.find((l) => l.source === "INSEE");
    // Distinct hue-free cues so the overlay survives greyscale (DESIGN.md §2).
    expect(wid?.dash).not.toBe(insee?.dash);
    expect(wid?.color).not.toBe(insee?.color);
    // Each line declares its own Convention — never collapsed into one.
    expect(wid?.convention).toBe("WID.world · par adulte · net");
    expect(insee?.convention).toBe("INSEE · par ménage · brut");
  });

  it("flags a source that returned no Observations", () => {
    const [line] = buildComparisonLines([series({ source: "DGFiP", points: [] })]);
    expect(line.hasData).toBe(false);
  });
});
