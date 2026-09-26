// Green-wave demo: ride J03 -> J08 (arriving on each junction's main road) with and without
// HariBatti speed advice. Uses the shared adviseSpeed (packages/core) on the mock signal plans.
// Simple kinematics: 0.5 s steps, stop at the line on red/amber, 2 s start-up loss after a stop.
import { adviseSpeed, type PhaseState } from "@haribatti/core";
import { approachProgram, nextGreen, offsetOf, stateAt } from "./mockSignals";
import { CORRIDOR, junctionById } from "./site";
import { tripFuel } from "./fuel";

export const SPACING_M = 500; // ASSUMED distance between neighbouring junctions
export const START_BEFORE_M = 300;
export const LIMIT_KMH = 50;
export const CRUISE_KMH = 40;
const DT = 0.5;
const STARTUP_LOSS_S = 2;

export type Ride = { stops: number; tripS: number; litres: number; co2g: number; track: { t: number; x: number; v: number }[] };

export function ride(startT: number, withAdvice: boolean): Ride {
  const lines = CORRIDOR.map((id, i) => ({ id, x: START_BEFORE_M + i * SPACING_M, steps: approachProgram(junctionById(id), true) }));
  const endX = lines[lines.length - 1]!.x + 200;
  let t = startT, x = 0, v = CRUISE_KMH / 3.6, stops = 0, stoppedFor = 0, wasStopped = false;
  const track: Ride["track"] = [];
  while (x < endX && t - startT < 1800) {
    const next = lines.find((l) => l.x > x + 0.01);
    let target = CRUISE_KMH / 3.6;
    if (next) {
      const d = next.x - x;
      const tt = t + offsetOf(next.id);
      const s = stateAt(next.steps, tt);
      if (withAdvice && d < 450) {
        const g = nextGreen(next.steps, tt);
        const phase: PhaseState = { junctionId: next.id, approachId: next.id, colour: s.colour, secondsRemaining: s.remaining, confidence: 0.9, source: "SIM", updatedAt: "" };
        const a = adviseSpeed(d, phase, g.startS, g.endS, LIMIT_KMH);
        if (a.kind === "HOLD_SPEED") target = a.kmh / 3.6;
      }
      const stopNeeded = s.colour !== "GREEN" && d < Math.max(8, (v * v) / (2 * 3)); // cannot clear on red
      if (stopNeeded && d <= v * DT + 0.5) {
        if (!wasStopped) stops += 1;
        wasStopped = true;
        v = 0;
        x = next.x - 0.5;
        stoppedFor += DT;
        t += DT;
        track.push({ t: t - startT, x, v });
        continue;
      }
      if (wasStopped && s.colour === "GREEN") {
        t += STARTUP_LOSS_S;
        wasStopped = false;
      }
    }
    // smooth speed changes (±1.5 m/s² ) towards the target
    v += Math.max(-1.5 * DT, Math.min(1.5 * DT, target - v));
    x += v * DT;
    t += DT;
    track.push({ t: t - startT, x, v });
  }
  void stoppedFor;
  const f = tripFuel(track);
  return { stops, tripS: t - startT, litres: f.litres, co2g: f.co2g, track };
}

/** Average stops and trip time over many departure times (so one lucky start cannot mislead). */
export function averageRides(withAdvice: boolean, departures = 60, baseT = 1_700_000_000) {
  let stops = 0, trip = 0, litres = 0, co2g = 0;
  for (let i = 0; i < departures; i++) {
    const r = ride(baseT + i * 37, withAdvice);
    stops += r.stops;
    trip += r.tripS;
    litres += r.litres;
    co2g += r.co2g;
  }
  const n = departures;
  return { stops: stops / n, tripS: trip / n, litres: litres / n, co2g: co2g / n };
}
