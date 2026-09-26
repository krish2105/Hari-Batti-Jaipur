// Live-wall alerts, computed from the PhaseState stream (pure functions, unit-tested).
// Spillback needs queue lengths, which PhaseState does not carry; it comes from CV or ITMS later.
import type { Colour, Phase } from "./types";

export type Track = { state: Phase; colourSince: number; lastSeen: number };
export type Alert = { kind: "dark" | "stuck" | "amber"; junctionId: string; approachId: string; seconds: number; colour?: Colour };

export const DARK_AFTER_S = 5; // no update for this long = signal dark (or feed lost)
export const STUCK_AFTER_S = 180; // one colour for longer than any sane phase
export const AMBER_AFTER_S = 10; // amber normally lasts 3-5 s

/** Update the per-approach tracker with one new message (time in ms). */
export function track(prev: Track | undefined, s: Phase, nowMs: number): Track {
  if (!prev || prev.state.colour !== s.colour) return { state: s, colourSince: nowMs, lastSeen: nowMs };
  return { state: s, colourSince: prev.colourSince, lastSeen: nowMs };
}

/** Hour of day from the simulator clock label ("18:15:03 IST, survey day …"), else the wall clock. */
export function clockHour(s: Phase, now: Date): number {
  const m = s.simClock?.match(/^(\d{2}):/);
  return m ? Number(m[1]) : now.getHours();
}

export function alertsFor(tracks: Iterable<Track>, nowMs: number): Alert[] {
  const out: Alert[] = [];
  for (const t of tracks) {
    const { junctionId, approachId, colour } = t.state;
    const quiet = (nowMs - t.lastSeen) / 1000;
    const held = (nowMs - t.colourSince) / 1000;
    if (quiet > DARK_AFTER_S) {
      out.push({ kind: "dark", junctionId, approachId, seconds: Math.round(quiet) });
      continue;
    }
    const hour = clockHour(t.state, new Date(nowMs));
    const daytime = hour >= 6 && hour < 22;
    if ((colour === "FLASHING_AMBER" && daytime) || (colour === "AMBER" && held > AMBER_AFTER_S)) {
      out.push({ kind: "amber", junctionId, approachId, seconds: Math.round(held), colour });
    } else if ((colour === "RED" || colour === "GREEN") && held > STUCK_AFTER_S) {
      out.push({ kind: "stuck", junctionId, approachId, seconds: Math.round(held), colour });
    }
  }
  return out;
}
