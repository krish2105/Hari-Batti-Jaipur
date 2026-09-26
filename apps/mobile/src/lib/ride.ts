// Ride-mode rules (pure, unit-tested): which signals are ahead, what to say, when to speak, when to
// lock the screen, and the trip summary. Safety rules live here and are tested:
//   - advice uses GLOSA v2 (packages/core) and is never above the speed limit minus 5 km/h,
//   - the words never tell anyone to go,
//   - low confidence shows a range, not a false exact number,
//   - no taps above 5 km/h.
import { adviseSpeed, type Advice, type PhaseState } from "@haribatti/core";
import { tr, type Lang } from "../i18n";
import { chainages, project, type LatLng } from "./geo";
import type { CorridorJunction, SignalView } from "./signals";

export const ON_CORRIDOR_M = 150; // further than this from the road: no advice
export const VOICE_AT_M = [400, 200, 100] as const;
export const TAP_LOCK_KMH = 5;
export const ENGINE_OFF_RED_S = 30;

/** Distance along the corridor (from J08) of every junction. */
export function junctionChainages(js: CorridorJunction[]): number[] {
  return chainages(js.map((j) => ({ lat: j.lat, lng: j.lng })));
}

export type Ahead = { junction: CorridorJunction; distanceM: number };

/** Up to three junctions ahead in the direction of travel (eastbound = towards J03). */
export function upcoming(chainage: number, eastbound: boolean, js: CorridorJunction[], at: number[], n = 3): Ahead[] {
  const out: Ahead[] = [];
  js.forEach((j, i) => {
    const d = eastbound ? at[i]! - chainage : chainage - at[i]!;
    if (d > -5) out.push({ junction: j, distanceM: Math.max(0, d) });
  });
  return out.sort((a, b) => a.distanceM - b.distanceM).slice(0, n);
}

/** Direction from two consecutive chainages (null while standing still). */
export function direction(prev: number | null, now: number, minMoveM = 3): boolean | null {
  if (prev === null || Math.abs(now - prev) < minMoveM) return null;
  return now > prev;
}

/** Match a GPS fix to the corridor. */
export function match(p: LatLng, js: CorridorJunction[]) {
  const r = project(p, js.map((j) => ({ lat: j.lat, lng: j.lng })));
  return { ...r, onCorridor: r.offset <= ON_CORRIDOR_M };
}

/** GLOSA v2 advice for one signal: first the next green window; if that cannot be caught within safe
 * speeds, the green after it (so the rider rolls up to the next green instead of stopping). */
export function adviceFor(distanceM: number, s: SignalView, limitKmh: number): Advice {
  const phase = { colour: s.colour, secondsRemaining: s.secondsRemaining, confidence: s.confidence } as PhaseState;
  const first = adviseSpeed(distanceM, phase, s.nextGreenStartS, s.nextGreenEndS, limitKmh);
  if (first.kind !== "PREPARE_TO_STOP" || s.followingGreenStartS === undefined || s.followingGreenEndS === undefined) return first;
  const later = adviseSpeed(distanceM, phase, s.followingGreenStartS, s.followingGreenEndS, limitKmh);
  return later.kind === "HOLD_SPEED" ? later : first;
}

/** The words for an advice, on screen and spoken. Never "go". */
export function phrase(a: Advice, s: SignalView, lang: Lang): string {
  if (a.kind === "HOLD_SPEED") return tr(lang, "hold", { kmh: a.kmh });
  if (a.kind === "UNKNOWN") return tr(lang, "unknown");
  if (s.colour === "RED") return `${tr(lang, "prepare")}. ${tr(lang, "redFor", { s: Math.round(s.secondsRemaining) })}`;
  return tr(lang, "prepare");
}

/** Countdown text: exact when confident, a range when not (crowd estimates), never a false exact number. */
export function countdownText(s: SignalView, lang: Lang): string {
  if (s.confidence >= 0.7) return String(Math.max(0, Math.round(s.secondsRemaining)));
  const spread = Math.max(5, Math.round(s.secondsRemaining * 0.35));
  const a = Math.max(0, Math.round(s.secondsRemaining - spread));
  return tr(lang, "range", { a, b: Math.round(s.secondsRemaining + spread) });
}

/** The voice threshold (400 / 200 / 100 m) crossed between two distances, if any. */
export function voiceThreshold(prevM: number | null, nowM: number): number | null {
  if (prevM === null) return null;
  return VOICE_AT_M.find((t) => prevM > t && nowM <= t) ?? null;
}

export const tapsLocked = (speedKmh: number) => speedKmh > TAP_LOCK_KMH;

/** Engine-off nudge: stopped at a red that still has more than 30 s. */
export const engineOffNudge = (speedKmh: number, s: SignalView | undefined) =>
  !!s && speedKmh < 3 && s.colour === "RED" && s.secondsRemaining > ENGINE_OFF_RED_S;

/** Trip statistics: a stop = below 5 km/h for at least 3 s (the same rule the field study uses). */
export class TripStats {
  distanceM = 0;
  stops = 0;
  waitedS = 0;
  private slowSince: number | null = null;
  private counted = false;
  private last: { t: number; chainage: number } | null = null;

  update(tS: number, speedKmh: number, chainage: number | null): void {
    if (this.last && chainage !== null) this.distanceM += Math.abs(chainage - this.last.chainage);
    if (speedKmh < 5) {
      if (this.slowSince === null) this.slowSince = tS;
      if (this.last) this.waitedS += tS - this.last.t;
      if (!this.counted && tS - this.slowSince >= 3) {
        this.stops += 1;
        this.counted = true;
      }
    } else {
      this.slowSince = null;
      this.counted = false;
    }
    if (chainage !== null) this.last = { t: tS, chainage };
    else if (this.last) this.last = { ...this.last, t: tS };
  }

  /** Fuel burnt while idling (ESTIMATE: about 0.6 L/h for a car, 0.15 L/h for a scooter). */
  idleFuelL(vehicle: "car" | "scooter"): number {
    return (this.waitedS / 3600) * (vehicle === "car" ? 0.6 : 0.15);
  }
}
