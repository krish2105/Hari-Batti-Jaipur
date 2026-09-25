// Offline signal generator: PhaseState for all 8 junctions with zero backend (source "SIM").
// Timings are the exported "Assumed timing – demand-proportional (2-phase, free left)" plans:
// main road green, amber 3 s, all-red 2 s, then cross roads green, amber 3 s, all-red 2 s.
// Deterministic from the clock, so every component shows the same countdown at the same moment.
import type { PhaseState, SignalColour } from "@haribatti/core";
import { site, type SiteJunction } from "./site";

export const AMBER_S = 3;
export const ALL_RED_S = 2;
export type Step = { colour: SignalColour; dur: number };

/** The repeating colour sequence one approach sees during a cycle. */
export function approachProgram(j: SiteJunction, main: boolean): Step[] {
  const { mainGreenS: gm, crossGreenS: gc } = j.plan;
  const mainSteps: Step[] = [
    { colour: "GREEN", dur: gm }, { colour: "AMBER", dur: AMBER_S },
    { colour: "RED", dur: ALL_RED_S + gc + AMBER_S + ALL_RED_S },
  ];
  const crossSteps: Step[] = [
    { colour: "RED", dur: gm + AMBER_S + ALL_RED_S }, { colour: "GREEN", dur: gc },
    { colour: "AMBER", dur: AMBER_S }, { colour: "RED", dur: ALL_RED_S },
  ];
  return main ? mainSteps : crossSteps;
}

export const cycleOf = (steps: Step[]) => steps.reduce((s, x) => s + x.dur, 0);

/** Fixed offset per junction so the corridor is not artificially synchronised. */
export const offsetOf = (junctionId: string) => (Number(junctionId.slice(1)) * 17) % 60;

/** Colour and seconds until it changes, at time t (seconds). */
export function stateAt(steps: Step[], t: number): { colour: SignalColour; remaining: number; index: number; into: number } {
  const c = cycleOf(steps);
  let x = ((t % c) + c) % c;
  for (let i = 0; i < steps.length; i++) {
    if (x < steps[i]!.dur) {
      // merge with following steps of the same colour (e.g. red + all-red)
      let remaining = steps[i]!.dur - x;
      for (let k = 1; k < steps.length; k++) {
        const next = steps[(i + k) % steps.length]!;
        if (next.colour !== steps[i]!.colour) break;
        remaining += next.dur;
      }
      return { colour: steps[i]!.colour, remaining, index: i, into: x };
    }
    x -= steps[i]!.dur;
  }
  return { colour: steps[0]!.colour, remaining: steps[0]!.dur, index: 0, into: 0 };
}

/** Seconds from time t until the next green starts (0 if green now) and when that green ends. */
export function nextGreen(steps: Step[], t: number): { startS: number; endS: number } {
  const now = stateAt(steps, t);
  if (now.colour === "GREEN") return { startS: 0, endS: now.remaining };
  let acc = now.remaining;
  const c = cycleOf(steps);
  for (let dt = 0; dt < c * 2; ) {
    const s = stateAt(steps, t + acc + 0.001);
    if (s.colour === "GREEN") return { startS: acc, endS: acc + s.remaining };
    acc += s.remaining;
    dt += s.remaining;
  }
  return { startS: acc, endS: acc };
}

export const approachId = (junctionId: string, name: string) =>
  `${junctionId}-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`;

/** All 32 approach states at time `nowMs` (defaults to the real clock). */
export function mockSignals(nowMs: number = Date.now()): PhaseState[] {
  const t = nowMs / 1000;
  const out: PhaseState[] = [];
  for (const j of site.junctions) {
    for (const a of j.approaches) {
      const s = stateAt(approachProgram(j, a.main), t + offsetOf(j.id));
      out.push({
        junctionId: j.id, approachId: approachId(j.id, a.name), colour: s.colour,
        secondsRemaining: Math.max(0, Math.ceil(s.remaining)), confidence: 0.9, source: "SIM",
        updatedAt: new Date(nowMs).toISOString(), timing: "ASSUMED", timingLabel: j.plan.label,
      });
    }
  }
  return out;
}
