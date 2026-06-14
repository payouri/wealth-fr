import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./client";

// Capture the URL the client builds, without a real network call.
function mockFetch(body: unknown) {
  const fetchMock = vi.fn(async (_input: string | URL) => ({
    ok: true,
    status: 200,
    statusText: "OK",
    json: async () => body,
  }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api.series", () => {
  it("carries the Convention params (concept + unite) into the query string", async () => {
    const fetchMock = mockFetch({ points: [] });
    await api.series({
      source: "WID",
      indicateur: "part_patrimoine",
      groupe: "top1",
      concept: "net",
      unite: "adulte",
    });

    const url = String(fetchMock.mock.calls[0]?.[0]);
    expect(url).toContain("/api/series?");
    // The Convention must survive into the request (CONTEXT.md guard rail).
    expect(url).toContain("concept=net");
    expect(url).toContain("unite=adulte");
    expect(url).toContain("source=WID");
  });

  it("omits unset optional params (unite derived server-side)", async () => {
    const fetchMock = mockFetch({ points: [] });
    // `concept` is required (ADR 0002); `unite` is optional and derived from source.
    await api.series({ source: "INSEE", indicateur: "gini", groupe: "ensemble", concept: "brut" });

    const url = String(fetchMock.mock.calls[0]?.[0]);
    expect(url).toContain("concept=brut");
    expect(url).not.toContain("unite=");
  });
});
