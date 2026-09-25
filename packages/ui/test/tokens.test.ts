// Every data source and every signal colour must have a token.
import { describe, expect, it } from "vitest";
import { DATA_SOURCE_LABELS } from "@haribatti/core";
import { signalColours, sourceBadgeColours } from "../src";

describe("tokens", () => {
  it("has a badge colour for every data source", () => {
    expect(Object.keys(sourceBadgeColours).sort()).toEqual(Object.keys(DATA_SOURCE_LABELS).sort());
  });

  it("uses valid hex colours", () => {
    for (const c of [...Object.values(signalColours), ...Object.values(sourceBadgeColours)]) {
      expect(c).toMatch(/^#[0-9A-F]{6}$/i);
    }
  });
});
