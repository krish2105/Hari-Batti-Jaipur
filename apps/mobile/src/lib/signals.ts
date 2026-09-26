// Signal phases for the app. Live: PhaseState from the API WebSocket (/ws/signals). Offline: the
// same ASSUMED 2-phase plans the website uses, generated from the clock (source SIM). Read-only.
import type { PhaseState, SignalColour } from "@haribatti/core";
import corridor from "../data/corridor.json";

export type Plan = { cycleS: number; mainGreenS: number; crossGreenS: number; label: string; source: string };
export type CorridorJunction = {
  id: string; name: string; lat: number; lng: number; positionStatus: string;
  eastboundApproach: string; westboundApproach: string; approachNames: Record<string, string>; plan: Plan;
};
export const CORRIDOR = corridor.junctions as unknown as CorridorJunction[];
export const SPEED_LIMIT_KMH = corridor.speedLimitKmh; // ASSUMED until the posted limits are surveyed

export const AMBER_S = 3;
export const ALL_RED_S = 2;
type Step = { colour: SignalColour; dur: number };

/** What the main road sees during one cycle: green, amber, then red while the cross road runs. */
export function mainProgram(p: Plan): Step[] {
  return [
    { colour: "GREEN", dur: p.mainGreenS },
    { colour: "AMBER", dur: AMBER_S },
    { colour: "RED", dur: ALL_RED_S + p.crossGreenS + AMBER_S + ALL_RED_S },
  ];
}

/** Same fixed offset per junction as the website, so both show the same simulated countdown. */
export const offsetOf = (junctionId: string) => (Number(junctionId.slice(1)) * 17) % 60;

export function stateAt(steps: Step[], t: number): { colour: SignalColour; remaining: number } {
  const c = steps.reduce((s, x) => s + x.dur, 0);
  let x = ((t % c) + c) % c;
  for (const s of steps) {
    if (x < s.dur) return { colour: s.colour, remaining: s.dur - x };
    x -= s.dur;
  }
  return { colour: steps[0]!.colour, remaining: steps[0]!.dur };
}

/** Everything the ride screen needs about one signal ahead. */
export type SignalView = {
  junctionId: string; approachId: string; colour: SignalColour; secondsRemaining: number; confidence: number;
  source: PhaseState["source"]; nextGreenStartS: number; nextGreenEndS: number; timingLabel: string;
  // the green after that one (one cycle later, ASSUMED plan length), for advice when the next is out of reach
  followingGreenStartS?: number; followingGreenEndS?: number;
};

/** Seconds until the main road's next green starts and ends, from the current colour (plan lengths are ASSUMED). */
export function nextGreenFrom(colour: SignalColour, remaining: number, p: Plan): { startS: number; endS: number } {
  if (colour === "GREEN") return { startS: 0, endS: remaining };
  if (colour === "AMBER" || colour === "FLASHING_AMBER") {
    const start = remaining + ALL_RED_S + p.crossGreenS + AMBER_S + ALL_RED_S;
    return { startS: start, endS: start + p.mainGreenS };
  }
  return { startS: remaining, endS: remaining + p.mainGreenS };
}

/** The green after the next one. While green now, the next main green begins after amber and the
 * cross-road phase; otherwise one full cycle after the next green starts. */
function following(colour: SignalColour, g: { startS: number; endS: number }, p: Plan) {
  const start = colour === "GREEN" ? g.endS + (p.cycleS - p.mainGreenS) : g.startS + p.cycleS;
  return { followingGreenStartS: start, followingGreenEndS: start + p.mainGreenS };
}

/** The signal a driver sees at junction j travelling east (towards J03) or west (towards J08). */
export function signalFor(j: CorridorJunction, eastbound: boolean, live: Map<string, PhaseState>, nowS: number): SignalView {
  const approachId = eastbound ? j.eastboundApproach : j.westboundApproach;
  const l = live.get(approachId);
  if (l) {
    const g = nextGreenFrom(l.colour, l.secondsRemaining, j.plan);
    return { junctionId: j.id, approachId, colour: l.colour, secondsRemaining: l.secondsRemaining, confidence: l.confidence,
      source: l.source, nextGreenStartS: g.startS, nextGreenEndS: g.endS, timingLabel: l.timingLabel ?? j.plan.label, ...following(l.colour, g, j.plan) };
  }
  const s = stateAt(mainProgram(j.plan), nowS + offsetOf(j.id));
  const g = nextGreenFrom(s.colour, s.remaining, j.plan);
  return { junctionId: j.id, approachId, colour: s.colour, secondsRemaining: Math.ceil(s.remaining), confidence: 0.9,
    source: "SIM", nextGreenStartS: g.startS, nextGreenEndS: g.endS, timingLabel: j.plan.label, ...following(s.colour, g, j.plan) };
}
