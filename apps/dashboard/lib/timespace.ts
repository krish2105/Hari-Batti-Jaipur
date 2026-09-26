// Time-space diagram maths for the corridor (pure, unit-tested).
// Main-road green is the first phase of each plan and starts at the junction's offset.
export type TsJunction = { id: string; x: number; cycle: number; green: number; offset: number };

/** Green windows [start, end) for the main road at one junction between t0 and t1. */
export function greenWindows(j: TsJunction, t0: number, t1: number): [number, number][] {
  const out: [number, number][] = [];
  let k = Math.floor((t0 - j.offset) / j.cycle) - 1;
  for (;;) {
    const s = j.offset + k * j.cycle;
    if (s >= t1) break;
    if (s + j.green > t0) out.push([Math.max(t0, s), Math.min(t1, s + j.green)]);
    k++;
  }
  return out;
}

function isGreen(j: TsJunction, t: number) {
  const phase = (((t - j.offset) % j.cycle) + j.cycle) % j.cycle;
  return phase < j.green;
}

function nextGreen(j: TsJunction, t: number) {
  const phase = (((t - j.offset) % j.cycle) + j.cycle) % j.cycle;
  return t + (j.cycle - phase);
}

/** Drive a car east at `speedMs` from x = 0 at time t0. Returns the path corners and stop count. */
export function drive(js: TsJunction[], speedMs: number, t0 = 0) {
  const pts: [number, number][] = [[0, t0]];
  let t = t0;
  let x = 0;
  let stops = 0;
  for (const j of js) {
    t += (j.x - x) / speedMs;
    x = j.x;
    pts.push([x, t]);
    if (!isGreen(j, t)) {
      t = nextGreen(j, t);
      stops++;
      pts.push([x, t]);
    }
  }
  return { pts, stops, travelS: t - t0 };
}

/** Offsets that start each main green when a car at `speedMs` arrives (a one-way green wave). */
export function waveOffsets(js: TsJunction[], speedMs: number): number[] {
  return js.map((j) => Math.round((j.x / speedMs) % j.cycle));
}
