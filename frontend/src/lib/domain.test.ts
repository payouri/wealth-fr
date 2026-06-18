import { describe, expect, it } from "vitest";
import type { Meta } from "@/api/types";
import {
  CONCENTRATION_GROUPES,
  conventionLabel,
  formatValue,
  groupeLabel,
  groupeOptions,
  indicateurMeta,
} from "./domain";

// A representative meta covering all three Groupe families plus standalone groups.
function makeMeta(overrides: Partial<Meta> = {}): Meta {
  return {
    sources: ["WID", "DGFiP"],
    indicateurs: ["part_patrimoine", "patrimoine_moyen", "seuil", "impot_moyen", "nb_foyers"],
    groupes: [],
    concepts: ["net", "immobilier"],
    unites: ["adulte", "foyer_fiscal"],
    millesimes: ["WID 2026", "DGFiP 2024"],
    availability: {},
    tranche_taux: {},
    annee_min: 2000,
    annee_max: 2021,
    ...overrides,
  };
}

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

describe("groupeLabel", () => {
  it("keeps the existing static fraction labels", () => {
    expect(groupeLabel("top1")).toBe("Top 1 %");
    expect(groupeLabel("ensemble")).toBe("Ensemble");
    expect(groupeLabel("redevables")).toBe("Redevables");
  });

  it("composes décile-de-patrimoine labels with extreme annotations on the fixed index", () => {
    expect(groupeLabel("decile_patrimoine_1")).toBe("Décile 1 de patrimoine (le plus faible)");
    expect(groupeLabel("decile_patrimoine_5")).toBe("Décile 5 de patrimoine");
    expect(groupeLabel("decile_patrimoine_10")).toBe("Décile 10 de patrimoine (le plus élevé)");
  });

  it("composes décile-de-revenu (RFR) labels", () => {
    expect(groupeLabel("decile_rfr_1")).toBe("Décile 1 de revenu (le plus faible)");
    expect(groupeLabel("decile_rfr_10")).toBe("Décile 10 de revenu (le plus élevé)");
  });

  it("annotates off the fixed index, so a missing 10th décile never mislabels the 9th", () => {
    // A series whose top décile is the 9th must NOT read the 9th as "le plus élevé".
    expect(groupeLabel("decile_patrimoine_9")).toBe("Décile 9 de patrimoine");
  });

  it("labels a tranche by its marginal rate (fr-FR) from the tranche_taux map", () => {
    const meta = makeMeta({
      tranche_taux: { tranche_marginale_2: 0.7, tranche_marginale_4: 1.25 },
    });
    expect(groupeLabel("tranche_marginale_2", meta)).toBe("Tranche à 0,7 %");
    expect(groupeLabel("tranche_marginale_4", meta)).toBe("Tranche à 1,25 %");
  });

  it("falls back to the raw code for a non-curated groupe (deep links keep resolving)", () => {
    expect(groupeLabel("p99.9p100")).toBe("p99.9p100");
    // A tranche with no rate available falls back rather than inventing one.
    expect(groupeLabel("tranche_marginale_3")).toBe("tranche_marginale_3");
  });
});

describe("CONCENTRATION_GROUPES", () => {
  it("is the canonical ordered set incl. top5 between top10 and top1", () => {
    expect([...CONCENTRATION_GROUPES]).toEqual([
      "ensemble",
      "bottom50",
      "middle40",
      "top50",
      "top10",
      "top5",
      "top1",
      "top0_1",
    ]);
  });
});

describe("groupeOptions", () => {
  it("curates concentration-bearing level indicateurs to the canonical set ∩ availability, excluding the percentile lattice", () => {
    const meta = makeMeta({
      availability: {
        WID: {
          patrimoine_moyen: ["p0p1", "p10p20", "ensemble", "top1", "top10", "p99.9p100", "top0_1"],
        },
      },
    });
    const groups = groupeOptions(meta, "WID", "patrimoine_moyen");
    const values = groups.flatMap((g) => g.options.map((o) => o.value));
    // canonical order, intersected with availability; lattice brackets dropped.
    expect(values).toEqual(["ensemble", "top10", "top1", "top0_1"]);
    expect(values).not.toContain("p0p1");
    expect(values).not.toContain("p99.9p100");
    // single ungrouped block (no family header) for the concentration family.
    expect(groups).toHaveLength(1);
    expect(groups[0].header).toBeNull();
  });

  it("groups DGFiP families under headers, numerically sorted, with standalone groups ungrouped on top", () => {
    const meta = makeMeta({
      tranche_taux: { tranche_marginale_2: 0.7, tranche_marginale_5: 1.5 },
      availability: {
        DGFiP: {
          seuil: [
            "redevables",
            "decile_patrimoine_10",
            "decile_patrimoine_2",
            "decile_patrimoine_1",
            "decile_rfr_1",
            "tranche_marginale_5",
            "tranche_marginale_2",
            "patrimoine_sup_10M",
          ],
        },
      },
    });
    const groups = groupeOptions(meta, "DGFiP", "seuil");
    // standalone groups first, ungrouped (no header).
    expect(groups[0].header).toBeNull();
    expect(groups[0].options.map((o) => o.value)).toEqual(["redevables", "patrimoine_sup_10M"]);
    // then a family header per present family.
    const headers = groups.map((g) => g.header);
    expect(headers).toContain("Patrimoine");
    expect(headers).toContain("Revenu fiscal (RFR)");
    expect(headers).toContain("Tranche marginale d'imposition");
    // patrimoine déciles numerically sorted (1, 2, 10 — not 1, 10, 2).
    const patri = groups.find((g) => g.header === "Patrimoine");
    expect(patri?.options.map((o) => o.value)).toEqual([
      "decile_patrimoine_1",
      "decile_patrimoine_2",
      "decile_patrimoine_10",
    ]);
    // tranches labelled by rate, numerically sorted.
    const tr = groups.find((g) => g.header === "Tranche marginale d'imposition");
    expect(tr?.options).toEqual([
      { value: "tranche_marginale_2", label: "Tranche à 0,7 %" },
      { value: "tranche_marginale_5", label: "Tranche à 1,5 %" },
    ]);
  });
});
