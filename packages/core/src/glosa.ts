// packages/core/glosa.ts — Green Light Optimal Speed Advisory, kept simple and safe.
// Copied from docs/03-mobile.md, plus one safety guard on rounding (see below).
// Safety rules: advice never says "go", and speed is capped at the speed limit minus 5 km/h.

import type { PhaseState } from "./types";

export type Advice =
  | { kind: "HOLD_SPEED"; kmh: number } // arrive during green at this speed
  | { kind: "PREPARE_TO_STOP"; redSecs: number } // green can't be caught safely
  | { kind: "UNKNOWN" }; // low confidence: show range only

/**
 * Suggest a steady speed that reaches the stop line during the next green, or say
 * "prepare to stop" when that is not possible within safe speeds.
 */
export function adviseSpeed(
  distanceM: number, // metres to the stop line
  phase: PhaseState, // current colour + secondsRemaining + confidence
  nextGreenStartS: number, // seconds until next green (0 if green now)
  nextGreenEndS: number, // seconds until that green ends
  speedLimitKmh: number, // posted limit for this road
): Advice {
  if (phase.confidence < 0.7) return { kind: "UNKNOWN" }; // never guess loudly

  const maxKmh = speedLimitKmh - 5; // safety cap below limit
  const minKmh = 15; // slower than this blocks traffic
  const toKmh = (mps: number) => mps * 3.6;

  // Arrival window: [green start + 2 s, green end - 3 s]
  const earliest = nextGreenStartS + 2;
  const latest = nextGreenEndS - 3;
  if (latest <= earliest) return { kind: "PREPARE_TO_STOP", redSecs: nextGreenStartS };

  const slowest = toKmh(distanceM / latest); // arrive at the last safe moment
  const fastest = toKmh(distanceM / Math.max(earliest, 0.1)); // arrive at the first safe moment

  const lo = Math.max(slowest, minKmh);
  const hi = Math.min(fastest, maxKmh);
  if (lo > hi) return { kind: "PREPARE_TO_STOP", redSecs: nextGreenStartS };

  let kmh = Math.round(Math.min(hi, lo + 5) / 5) * 5; // round to 5s, easy to hold

  // Safety guard (not in the doc): rounding up can push past the cap when the limit
  // is not a multiple of 5 (limit 48 -> cap 43 -> 45). Round down instead, and if no
  // multiple of 5 fits inside [lo, hi], do not give a speed at all.
  if (kmh > hi) kmh = Math.floor(hi / 5) * 5;
  if (kmh < lo) return { kind: "PREPARE_TO_STOP", redSecs: nextGreenStartS };

  return { kind: "HOLD_SPEED", kmh };
}
