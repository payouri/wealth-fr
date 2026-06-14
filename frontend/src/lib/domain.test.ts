import { describe, expect, it } from "vitest";
import { conventionLabel, formatValue, indicateurMeta } from "./domain";

// fr-FR uses a comma decimal and a (narrow) space thousands separator; normalise
// whitespace so the assertions don't hinge on the exact space codepoint.
const norm = (s: string) => s.replace(/[  \s]/g, " ");

describe("formatValue", () => {
  it("formats shares as a percentage with one decimal", () => {
    expect(norm(formatValue(27.09, "%"))).toBe("27,1 %");
  });

  it("formats the Gini index with three decimals", () => {
    expect(formatValue(0.6938, "indice")).toBe("0,694");
  });

  it("formats counts with a thousands separator and a euro suffix for levels", () => {
    expect(norm(formatValue(186000, "effectif"))).toBe("186 000");
    expect(norm(formatValue(12000, "euros"))).toBe("12 000 €");
  });
});

describe("indicateurMeta", () => {
  it("marks part_patrimoine as a share and not a level (euros toggle inert)", () => {
    expect(indicateurMeta("part_patrimoine")).toMatchObject({ isShare: true, isLevel: false });
  });

  it("marks impot_moyen as a level (euros toggle active)", () => {
    expect(indicateurMeta("impot_moyen").isLevel).toBe(true);
  });
});

describe("conventionLabel", () => {
  it("carries source, unité and concept so a line is never read as merged", () => {
    expect(conventionLabel("WID", "adulte", "net")).toBe("WID.world · par adulte · net");
  });
});
