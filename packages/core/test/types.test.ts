// Checks the source labels cover every allowed data source, including SURVEY.
import { describe, expect, it } from "vitest";
import { DATA_SOURCE_LABELS, type PhaseState } from "../src";

describe("DATA_SOURCE_LABELS", () => {
  it("has exactly the five allowed sources", () => {
    expect(Object.keys(DATA_SOURCE_LABELS).sort()).toEqual(["CROWD", "FIELD", "ITMS", "SIM", "SURVEY"]);
  });

  it("labels survey counts as 'Survey, May 2026'", () => {
    expect(DATA_SOURCE_LABELS.SURVEY).toBe("Survey, May 2026");
  });
});

describe("PhaseState from the simulator", () => {
  it("accepts the simulator's optional labels", () => {
    const msg: PhaseState = {
      junctionId: "J03",
      approachId: "J03-mansarover-metro",
      colour: "GREEN",
      secondsRemaining: 17,
      confidence: 0.9,
      source: "SIM",
      updatedAt: "2026-09-25T21:01:57+00:00",
      timing: "ASSUMED",
      timingLabel: "Assumed timing – demand-proportional (2-phase, free left)",
      geometry: "SCHEMATIC",
      geometryLabel: "Schematic network – coordinates pending",
      simClock: "18:16:10 IST, survey day 2026-05-11",
    };
    expect(msg.source).toBe("SIM");
  });
});
