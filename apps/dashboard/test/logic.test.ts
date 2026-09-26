// Unit tests for the dashboard's pure logic: alerts, time-space maths, fairness fixes, i18n keys.
import { describe, expect, it } from "vitest";
import { alertsFor, track, type Track } from "@/lib/alerts";
import { drive, greenWindows, waveOffsets, type TsJunction } from "@/lib/timespace";
import { extraGreen } from "@/lib/fairness";
import { improved, insightKey, progressShare } from "@/lib/pilotMath";
import en from "@/messages/en.json";
import hi from "@/messages/hi.json";
import type { Phase } from "@/lib/types";

const phase = (colour: Phase["colour"], simClock = "12:00:00 IST, survey day 2026-05-11"): Phase => ({
  junctionId: "J05", approachId: "J05-a", colour, secondsRemaining: 10, confidence: 0.9, source: "SIM", updatedAt: "", simClock,
});

describe("alerts", () => {
  it("flags a signal that stopped updating as dark", () => {
    const t = track(undefined, phase("RED"), 0);
    expect(alertsFor([t], 6_000)[0]).toMatchObject({ kind: "dark", seconds: 6 });
    expect(alertsFor([t], 4_000)).toEqual([]);
  });
  it("flags one colour held for more than 3 minutes as stuck", () => {
    let t: Track = track(undefined, phase("RED"), 0);
    t = track(t, phase("RED"), 181_000);
    expect(alertsFor([t], 181_000)[0]).toMatchObject({ kind: "stuck", colour: "RED" });
  });
  it("resets the timer when the colour changes", () => {
    let t: Track = track(undefined, phase("RED"), 0);
    t = track(t, phase("GREEN"), 170_000);
    t = track(t, phase("GREEN"), 200_000);
    expect(alertsFor([t], 200_000)).toEqual([]);
  });
  it("flags flashing amber only in the daytime (sim clock)", () => {
    const day = track(undefined, phase("FLASHING_AMBER", "14:00:00 IST"), 0);
    const night = track(undefined, phase("FLASHING_AMBER", "02:00:00 IST"), 0);
    expect(alertsFor([day], 1000)[0]?.kind).toBe("amber");
    expect(alertsFor([night], 1000)).toEqual([]);
  });
});

describe("time-space", () => {
  const js: TsJunction[] = [0, 1, 2, 3].map((i) => ({ id: `J${i}`, x: 500 * (i + 1), cycle: 120, green: 25, offset: 0 }));
  it("lists green windows inside the range", () => {
    expect(greenWindows(js[0]!, 0, 250)).toEqual([[0, 25], [120, 145], [240, 250]]);
  });
  it("a car at 36 km/h meets red at every junction when offsets are all zero", () => {
    // arrives at 50 s, 100 s…: never inside the 0–25 s green of a 120 s cycle
    expect(drive(js, 10).stops).toBeGreaterThanOrEqual(3);
  });
  it("wave offsets let the same car pass every junction without stopping", () => {
    const off = waveOffsets(js, 10);
    expect(off).toEqual([50, 100, 30, 80]);
    const wave = js.map((j, i) => ({ ...j, offset: off[i] ?? 0 }));
    expect(drive(wave, 10).stops).toBe(0);
    expect(drive(wave, 10).travelS).toBeCloseTo(200);
  });
});

describe("fairness fix", () => {
  it("adds the green needed to reach a ratio of 1", () => {
    expect(extraGreen(20, 0.8)).toBe(5);
    expect(extraGreen(20, 1.2)).toBeNull();
    expect(extraGreen(null, 0.5)).toBeNull();
  });
});

describe("i18n", () => {
  const keys = (o: Record<string, unknown>, p = ""): string[] =>
    Object.entries(o).flatMap(([k, v]) => (v && typeof v === "object" ? keys(v as Record<string, unknown>, `${p}${k}.`) : [`${p}${k}`]));
  it("Hindi has exactly the same keys as English", () => {
    expect(keys(hi).sort()).toEqual(keys(en).sort());
  });
});

describe("plan clock (offline fallback)", async () => {
  const { program, stateAt, planStates } = await import("@/lib/planClock");
  it("main and cross programs fill the same cycle", () => {
    const sum = (m: boolean) => program(38, 12, m).reduce((a, s) => a + s.dur, 0);
    expect(sum(true)).toBe(38 + 12 + 10);
    expect(sum(false)).toBe(sum(true));
  });
  it("merges red and all-red into one countdown", () => {
    const s = stateAt(program(38, 12, true), 41);
    expect(s).toEqual({ colour: "RED", remaining: 19 });
  });
  it("labels every simulated phase SIM with ASSUMED timing", () => {
    const js = [{ id: "J05", approaches: [{ id: "J05-a", isMain: true }, { id: "J05-b", isMain: false }] }] as never;
    const lib = { available: true, plans: { demand2: { label: "x", junctions: { J05: { cycleS: 60, mainGreenS: 38, crossGreenS: 12 } } } } } as never;
    const out = planStates(js, lib, 0);
    expect(out).toHaveLength(2);
    expect(out.every((p) => p.source === "SIM" && p.timing === "ASSUMED")).toBe(true);
    expect(out.find((p) => p.approachId === "J05-a")!.colour).not.toBe(out.find((p) => p.approachId === "J05-b")!.colour);
  });
});

// ---- Pilot operations (P8 W13) ----

describe("pilot helpers", () => {
  it("progress is day / days, clamped, and 0 before the pilot has dates", () => {
    expect(progressShare(null, null)).toBe(0);
    expect(progressShare(30, 60)).toBe(0.5);
    expect(progressShare(90, 60)).toBe(1);
  });
  it("improvement follows the measure's direction and needs both values", () => {
    expect(improved("lower", 50, 40)).toBe(true);
    expect(improved("lower", 40, 50)).toBe(false);
    expect(improved("higher", 60, 80)).toBe(true);
    expect(improved("lower", null, 40)).toBeNull();
    expect(improved("lower", 40, 40)).toBeNull();
  });
  it("insight keys are stable and match the API's allowed pattern", () => {
    const k = insightKey("copilot.answer", "Which junction is worst at 18:00?");
    expect(k).toBe(insightKey("copilot.answer", "Which junction is worst at 18:00?"));
    expect(k).not.toBe(insightKey("copilot.answer", "Something else"));
    expect(k).toMatch(/^[A-Za-z0-9_.:-]{2,80}$/);
  });
});
