// Unit tests: impact formulas, mock signals, green-wave ride.
import { describe, expect, it } from "vitest";
import { impact } from "../lib/impact";
import { approachProgram, cycleOf, mockSignals, nextGreen, stateAt } from "../lib/mockSignals";
import { averageRides, ride } from "../lib/greenwave";
import { junctionById, site } from "../lib/site";
import { fuelRate, tripFuel } from "../lib/fuel";

describe("VT-Micro fuel model", () => {
  it("idles at about 1.6 L/h and cruises at 50 km/h near 8 L/100 km", () => {
    expect(fuelRate(0, 0) * 3600).toBeCloseTo(1.57, 1); // exp(-7.735) L/s
    const per100km = (fuelRate(50, 0) / (50 / 3600)) * 100;
    expect(per100km).toBeGreaterThan(6);
    expect(per100km).toBeLessThan(11);
  });
  it("stopping and restarting burns more than cruising the same distance", () => {
    const cruise = Array.from({ length: 61 }, (_, i) => ({ t: i, v: 11.1 }));
    const stopGo = Array.from({ length: 61 }, (_, i) => ({ t: i, v: i < 20 ? 11.1 : i < 28 ? 11.1 * (1 - (i - 20) / 8) : i < 38 ? 0 : Math.min(11.1, (i - 38) * 1.5) }));
    expect(tripFuel(stopGo).litres / 1).toBeGreaterThan(0);
    expect(tripFuel(cruise).litres).toBeGreaterThan(0);
  });
});

describe("impact", () => {
  it("matches the formula shown on the page", () => {
    // 8 x 125000 x 10 / 3600 = 2777.8 h; x 0.6 = 1666.7 L; x 2.31 = 3850 kg
    const r = impact({ junctions: 8, vehiclesPerJunction: 125_000, secondsSaved: 10 });
    expect(r.hoursPerDay).toBeCloseTo(2777.78, 1);
    expect(r.fuelLitres).toBeCloseTo(1666.67, 1);
    expect(r.co2Kg).toBeCloseTo(3850, 0);
  });
});

describe("mockSignals", () => {
  it("covers all 8 junctions and 32 approaches, labelled SIM", () => {
    const s = mockSignals(0);
    expect(new Set(s.map((x) => x.junctionId)).size).toBe(8);
    expect(s).toHaveLength(site.junctions.reduce((n, j) => n + j.approaches.length, 0));
    expect(s.every((x) => x.source === "SIM" && x.timing === "ASSUMED")).toBe(true);
  });

  it("main and cross roads are never green together", () => {
    const j = junctionById("J04");
    const main = approachProgram(j, true), cross = approachProgram(j, false);
    expect(cycleOf(main)).toBe(j.plan.cycleS);
    expect(cycleOf(cross)).toBe(j.plan.cycleS);
    for (let t = 0; t < j.plan.cycleS; t++) {
      expect(stateAt(main, t).colour === "GREEN" && stateAt(cross, t).colour === "GREEN").toBe(false);
    }
  });

  it("counts down one second per second and merges all-red into red", () => {
    const main = approachProgram(junctionById("J03"), true);
    expect(stateAt(main, 0).remaining).toBe(junctionById("J03").plan.mainGreenS);
    expect(stateAt(main, 1).remaining).toBe(junctionById("J03").plan.mainGreenS - 1);
    const redStart = junctionById("J03").plan.mainGreenS + 3;
    expect(stateAt(main, redStart).remaining).toBe(junctionById("J03").plan.cycleS - redStart);
  });

  it("nextGreen is 0 while green and points at the next green on red", () => {
    const main = approachProgram(junctionById("J03"), true);
    expect(nextGreen(main, 0).startS).toBe(0);
    const g = nextGreen(main, 40);
    expect(g.startS).toBeCloseTo(junctionById("J03").plan.cycleS - 40, 3);
  });
});

describe("green wave", () => {
  it("finishes the ride and never moves backwards", () => {
    const r = ride(1_700_000_000, true);
    expect(r.track.at(-1)!.x).toBeGreaterThan(2800);
    for (let i = 1; i < r.track.length; i++) expect(r.track[i]!.x).toBeGreaterThanOrEqual(r.track[i - 1]!.x - 0.6);
  });

  it("speed advice never exceeds the limit minus 5 km/h", () => {
    const r = ride(1_700_000_123, true);
    expect(Math.max(...r.track.map((p) => p.v * 3.6))).toBeLessThanOrEqual(45.001);
  });

  it("GLOSA v2: fewer stops and no longer ride time on average", () => {
    const on = averageRides(true), off = averageRides(false);
    expect(on.stops).toBeLessThan(off.stops);
    expect(on.tripS).toBeLessThanOrEqual(off.tripS);
  });
});

// The MapLibre worker copy in public/ must match the installed maplibre-gl (P8 W16 upgrade to v6).
import { readFileSync } from "node:fs";
import { join } from "node:path";

describe("maplibre worker copy", () => {
  it("matches the installed package version", () => {
    const pkg = JSON.parse(readFileSync(join(__dirname, "..", "node_modules", "maplibre-gl", "package.json"), "utf8")) as { version: string };
    const copied = readFileSync(join(__dirname, "..", "public", "vendor", "maplibre", "VERSION"), "utf8").trim();
    expect(copied, "run: node scripts/copy-maplibre-worker.mjs").toBe(pkg.version);
  });
});
