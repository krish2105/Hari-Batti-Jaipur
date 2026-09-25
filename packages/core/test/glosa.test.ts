// Unit tests for adviseSpeed (GLOSA). The 300 m case is the worked example in docs/03-mobile.md.
import { describe, expect, it } from "vitest";
import { adviseSpeed, type PhaseState } from "../src";

// A red light with high confidence (simulated), used by most tests.
const red = (confidence = 0.95): PhaseState => ({
  junctionId: "J03",
  approachId: "J03-A1",
  colour: "RED",
  secondsRemaining: 20,
  confidence,
  source: "SIM",
  updatedAt: "2026-09-26T10:00:00Z",
});

describe("adviseSpeed", () => {
  it("worked example: 300 m, green 20–50 s, limit 50 → hold 30 km/h", () => {
    expect(adviseSpeed(300, red(), 20, 50, 50)).toEqual({ kind: "HOLD_SPEED", kmh: 30 });
  });

  it("returns UNKNOWN when confidence is below 0.7", () => {
    expect(adviseSpeed(300, red(0.69), 20, 50, 50)).toEqual({ kind: "UNKNOWN" });
  });

  it("says prepare to stop when the green window is too short", () => {
    // earliest = 22 s, latest = 22 s -> no window
    expect(adviseSpeed(300, red(), 20, 25, 50)).toEqual({ kind: "PREPARE_TO_STOP", redSecs: 20 });
  });

  it("says prepare to stop when catching green would need speeding", () => {
    // 600 m in at most 18 s is ~120 km/h, far above the 45 km/h cap
    expect(adviseSpeed(600, red(), 0, 21, 50)).toEqual({ kind: "PREPARE_TO_STOP", redSecs: 0 });
  });

  it("never advises above the speed limit minus 5 km/h", () => {
    for (const limit of [30, 40, 48, 50, 60]) {
      for (const d of [50, 150, 300, 500]) {
        const a = adviseSpeed(d, red(), 0, 60, limit);
        if (a.kind === "HOLD_SPEED") expect(a.kmh).toBeLessThanOrEqual(limit - 5);
      }
    }
  });

  it("rounds down, not up, when the limit is not a multiple of 5 (limit 48 → 40, not 45)", () => {
    // window 2–28 s: lo ~38.6 km/h, cap 43. The doc's rounding alone would give 45.
    expect(adviseSpeed(300, red(), 0, 31, 48)).toEqual({ kind: "HOLD_SPEED", kmh: 40 });
  });

  it("says prepare to stop when no multiple of 5 fits under the cap", () => {
    // window 2–26 s: lo ~41.5 km/h, cap 43. 45 is too fast and 40 arrives after green.
    expect(adviseSpeed(300, red(), 0, 29, 48)).toEqual({ kind: "PREPARE_TO_STOP", redSecs: 0 });
  });

  it("gives a steady speed when the light is green now and the stop line is close", () => {
    const green: PhaseState = { ...red(), colour: "GREEN" };
    const a = adviseSpeed(100, green, 0, 30, 50);
    expect(a.kind).toBe("HOLD_SPEED");
    if (a.kind === "HOLD_SPEED") {
      expect(a.kmh % 5).toBe(0);
      expect(a.kmh).toBeGreaterThanOrEqual(15);
      expect(a.kmh).toBeLessThanOrEqual(45);
    }
  });

  it("never returns any kind that means 'go'", () => {
    const kinds = new Set(["HOLD_SPEED", "PREPARE_TO_STOP", "UNKNOWN"]);
    for (const d of [20, 100, 300, 800]) {
      expect(kinds.has(adviseSpeed(d, red(), 10, 40, 50).kind)).toBe(true);
    }
  });
});
