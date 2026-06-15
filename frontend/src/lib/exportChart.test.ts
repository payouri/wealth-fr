import { describe, expect, it } from "vitest";
import { exportStem } from "./exportChart";

describe("exportStem", () => {
  it("joins filter parts into a safe file stem", () => {
    expect(exportStem(["WID", "part_patrimoine", "top1"])).toBe("WID_part_patrimoine_top1");
  });

  it("drops empty parts and sanitises separators", () => {
    expect(exportStem(["WID", undefined, "", "top 1%"])).toBe("WID_top-1-");
  });

  it("falls back to a default stem when nothing usable is given", () => {
    expect(exportStem([undefined, ""])).toBe("export");
  });
});
