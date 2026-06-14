import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "./client";

describe("ApiError.ambiguousConvention", () => {
  it("exposes the choices on a 422 ambiguous_convention body", () => {
    const err = new ApiError(422, {
      error: "ambiguous_convention",
      choices: [
        { unite: "foyer_fiscal", concept_patrimoine: "total" },
        { unite: "foyer_fiscal", concept_patrimoine: "immobilier" },
      ],
    });
    expect(err.ambiguousConvention?.choices).toHaveLength(2);
  });

  it("returns null for any other failure", () => {
    expect(new ApiError(500, "boom").ambiguousConvention).toBeNull();
    expect(new ApiError(422, { error: "other" }).ambiguousConvention).toBeNull();
  });
});

describe("api.series error handling", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("rejects with an ApiError carrying the parsed 422 detail (ADR 0002)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 422,
        statusText: "Unprocessable Content",
        json: async () => ({
          detail: {
            error: "ambiguous_convention",
            choices: [{ unite: "foyer_fiscal", concept_patrimoine: "total" }],
          },
        }),
      })),
    );

    await expect(
      api.series({ source: "DGFiP", indicateur: "nb_foyers", groupe: "redevables" }),
    ).rejects.toMatchObject({ status: 422 });

    try {
      await api.series({ source: "DGFiP", indicateur: "nb_foyers", groupe: "redevables" });
    } catch (e) {
      expect((e as ApiError).ambiguousConvention?.choices[0]?.concept_patrimoine).toBe("total");
    }
  });
});
