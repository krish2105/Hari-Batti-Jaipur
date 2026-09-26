// Ride-mode safety and logic tests: map matching, signals ahead, advice cap, wording, voice
// thresholds, range display, screen lock and trip statistics.
import { describe, expect, it } from "vitest";
import { STRINGS, type Lang } from "../src/i18n";
import { metres, project } from "../src/lib/geo";
import { adviceFor, countdownText, direction, engineOffNudge, junctionChainages, match, phrase, tapsLocked, TripStats, upcoming, voiceThreshold } from "../src/lib/ride";
import { CORRIDOR, mainProgram, nextGreenFrom, signalFor, SPEED_LIMIT_KMH, stateAt, type SignalView } from "../src/lib/signals";

const at = junctionChainages(CORRIDOR);
const view = (over: Partial<SignalView> = {}): SignalView => ({
  junctionId: "J05", approachId: "J05-mansarover-metro", colour: "RED", secondsRemaining: 20, confidence: 0.9, source: "SIM",
  nextGreenStartS: 20, nextGreenEndS: 58, timingLabel: "ASSUMED", ...over,
});

describe("corridor geometry", () => {
  it("orders the junctions west to east with realistic spacing", () => {
    expect(CORRIDOR.map((j) => j.id)).toEqual(["J08", "J07", "J06", "J05", "J04", "J03"]);
    for (let i = 1; i < at.length; i++) {
      const gap = at[i]! - at[i - 1]!;
      expect(gap).toBeGreaterThan(200);
      expect(gap).toBeLessThan(1500);
    }
  });
  it("a point on the road projects onto it; one 1 km away is off the corridor", () => {
    const j5 = CORRIDOR[3]!;
    expect(project({ lat: j5.lat, lng: j5.lng }, CORRIDOR).offset).toBeLessThan(1);
    expect(match({ lat: j5.lat + 0.01, lng: j5.lng }, CORRIDOR).onCorridor).toBe(false);
    expect(metres({ lat: 26.85, lng: 75.76 }, { lat: 26.86, lng: 75.76 })).toBeCloseTo(1112, -1);
  });
});

describe("signals ahead", () => {
  it("eastbound from J06 sees J05, J04, J03 in order; westbound sees J07, J08", () => {
    const c = at[2]! + 50; // just past J06
    expect(upcoming(c, true, CORRIDOR, at).map((a) => a.junction.id)).toEqual(["J05", "J04", "J03"]);
    expect(upcoming(c, false, CORRIDOR, at).map((a) => a.junction.id)).toEqual(["J06", "J07", "J08"]);
  });
  it("direction needs real movement", () => {
    expect(direction(100, 101)).toBeNull();
    expect(direction(100, 120)).toBe(true);
    expect(direction(120, 100)).toBe(false);
  });
  it("offline countdowns follow the assumed plan and are labelled SIM", () => {
    const s = signalFor(CORRIDOR[3]!, true, new Map(), 0);
    expect(s.source).toBe("SIM");
    const prog = mainProgram(CORRIDOR[3]!.plan);
    expect(prog.reduce((a, x) => a + x.dur, 0)).toBe(CORRIDOR[3]!.plan.cycleS);
    expect(stateAt(prog, 0).colour).toBe("GREEN");
    expect(nextGreenFrom("RED", 10, CORRIDOR[3]!.plan)).toEqual({ startS: 10, endS: 10 + CORRIDOR[3]!.plan.mainGreenS });
  });
});

describe("advice safety", () => {
  const langs: Lang[] = ["en", "hi"];
  it("never advises above the speed limit minus 5 km/h", () => {
    for (let d = 20; d <= 800; d += 20)
      for (let r = 0; r <= 90; r += 5) {
        const a = adviceFor(d, view({ colour: "RED", secondsRemaining: r, nextGreenStartS: r, nextGreenEndS: r + 38 }), SPEED_LIMIT_KMH);
        if (a.kind === "HOLD_SPEED") expect(a.kmh).toBeLessThanOrEqual(SPEED_LIMIT_KMH - 5);
      }
  });
  it("the 300 m worked example says 'hold 45 km/h' (GLOSA v2)", () => {
    const a = adviceFor(300, view({ secondsRemaining: 20, nextGreenStartS: 20, nextGreenEndS: 50 }), 50);
    expect(a).toEqual({ kind: "HOLD_SPEED", kmh: 45 });
  });
  it("no phrase in any language tells anyone to go", () => {
    const forbidden = /\bgo\b|\bgo ahead\b|\bproceed\b|you can make it|जाइए|जाओ|निकलिए|निकल जाइए|चलिए/i;
    for (const lang of langs)
      for (let d = 30; d <= 600; d += 30)
        for (const colour of ["RED", "GREEN", "AMBER"] as const)
          for (const conf of [0.5, 0.9]) {
            const s = view({ colour, confidence: conf, secondsRemaining: 15, nextGreenStartS: colour === "GREEN" ? 0 : 15, nextGreenEndS: 45 });
            expect(phrase(adviceFor(d, s, 50), s, lang)).not.toMatch(forbidden);
          }
    for (const lang of langs) for (const v of Object.values(STRINGS[lang])) expect(v).not.toMatch(/\bgo\b|you can make it/i);
  });
  it("when this green cannot be caught, advises a steady speed for the following green instead of stopping", () => {
    // 480 m away, green ends in 23 s (needs ~86 km/h): the next green (after a 25 s red) can be caught
    const s = view({ colour: "GREEN", secondsRemaining: 23, nextGreenStartS: 0, nextGreenEndS: 23, followingGreenStartS: 48, followingGreenEndS: 105 });
    const a = adviceFor(480, s, 50);
    expect(a.kind).toBe("HOLD_SPEED");
    if (a.kind === "HOLD_SPEED") expect(a.kmh).toBeLessThanOrEqual(45);
    // no following window known: falls back to "prepare to stop"
    expect(adviceFor(480, view({ colour: "GREEN", secondsRemaining: 23, nextGreenStartS: 0, nextGreenEndS: 23 }), 50).kind).toBe("PREPARE_TO_STOP");
  });
  it("low confidence shows a range, high confidence an exact number", () => {
    expect(countdownText(view({ confidence: 0.95, secondsRemaining: 23 }), "en")).toBe("23");
    expect(countdownText(view({ confidence: 0.6, secondsRemaining: 30 }), "en")).toMatch(/^\d+–\d+ s$/);
    expect(adviceFor(200, view({ confidence: 0.5 }), 50).kind).toBe("UNKNOWN");
  });
});

describe("voice, screen lock and trip", () => {
  it("speaks once at 400, 200 and 100 m", () => {
    expect(voiceThreshold(410, 395)).toBe(400);
    expect(voiceThreshold(205, 199)).toBe(200);
    expect(voiceThreshold(150, 140)).toBeNull();
    expect(voiceThreshold(null, 90)).toBeNull();
  });
  it("locks taps above 5 km/h", () => {
    expect(tapsLocked(4)).toBe(false);
    expect(tapsLocked(6)).toBe(true);
  });
  it("nudges engine-off only when stopped at a long red", () => {
    expect(engineOffNudge(0, view({ colour: "RED", secondsRemaining: 45 }))).toBe(true);
    expect(engineOffNudge(0, view({ colour: "RED", secondsRemaining: 20 }))).toBe(false);
    expect(engineOffNudge(20, view({ colour: "RED", secondsRemaining: 45 }))).toBe(false);
  });
  it("counts a stop after 3 s below 5 km/h and sums the time waited", () => {
    const t = new TripStats();
    [[0, 30, 0], [1, 30, 8], [2, 2, 10], [3, 1, 10], [4, 1, 10], [5, 1, 10], [6, 30, 18], [7, 30, 26]].forEach(([s, v, c]) => t.update(s!, v!, c!));
    expect(t.stops).toBe(1);
    expect(t.waitedS).toBeCloseTo(4, 5);
    expect(t.distanceM).toBe(26);
  });
});

describe("languages", () => {
  it("English and Hindi have the same keys and no empty strings", () => {
    expect(Object.keys(STRINGS.hi).sort()).toEqual(Object.keys(STRINGS.en).sort());
    for (const v of Object.values(STRINGS.hi)) expect(v.length).toBeGreaterThan(0);
  });
});
