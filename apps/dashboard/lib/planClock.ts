// Offline fallback for the live wall and junction pages: when no live feed arrives, run the ASSUMED
// 2-phase plans on the clock (same maths as the website and the app) and label everything SIM.
// Pure maths is exported for tests; the hook loads /junctions and /plans/library once.
import { useEffect, useState } from "react";
import { api } from "./api";
import type { Colour, JunctionInfo, Phase, PlanLibrary } from "./types";

export const AMBER_S = 3;
export const ALL_RED_S = 2;
type Step = { colour: Colour; dur: number };

/** The colour sequence one approach sees during a cycle (main road first, then the cross road). */
export function program(mainGreen: number, crossGreen: number, isMain: boolean): Step[] {
  return isMain
    ? [{ colour: "GREEN", dur: mainGreen }, { colour: "AMBER", dur: AMBER_S }, { colour: "RED", dur: ALL_RED_S + crossGreen + AMBER_S + ALL_RED_S }]
    : [{ colour: "RED", dur: mainGreen + AMBER_S + ALL_RED_S }, { colour: "GREEN", dur: crossGreen }, { colour: "AMBER", dur: AMBER_S }, { colour: "RED", dur: ALL_RED_S }];
}

/** Colour and seconds left at time t (consecutive steps of the same colour are merged). */
export function stateAt(steps: Step[], t: number): { colour: Colour; remaining: number } {
  const c = steps.reduce((a, s) => a + s.dur, 0);
  let x = ((t % c) + c) % c;
  for (let i = 0; i < steps.length; i++) {
    const s = steps[i]!;
    if (x < s.dur) {
      let remaining = s.dur - x;
      for (let k = 1; k < steps.length; k++) {
        const n = steps[(i + k) % steps.length]!;
        if (n.colour !== s.colour) break;
        remaining += n.dur;
      }
      return { colour: s.colour, remaining };
    }
    x -= s.dur;
  }
  return { colour: steps[0]!.colour, remaining: steps[0]!.dur };
}

export const offsetOf = (junctionId: string) => (Number(junctionId.slice(1)) * 17) % 60;

export function planStates(js: JunctionInfo[], lib: PlanLibrary, nowS: number): Phase[] {
  const plans = lib.plans?.demand2?.junctions ?? {};
  const out: Phase[] = [];
  for (const j of js) {
    const p = plans[j.id];
    if (!p?.mainGreenS || !p.crossGreenS) continue;
    for (const a of j.approaches) {
      const s = stateAt(program(p.mainGreenS, p.crossGreenS, a.isMain), nowS + offsetOf(j.id));
      out.push({ junctionId: j.id, approachId: a.id, colour: s.colour, secondsRemaining: Math.ceil(s.remaining), confidence: 0.6,
        source: "SIM", updatedAt: new Date(nowS * 1000).toISOString(), timing: "ASSUMED", timingLabel: lib.plans?.demand2?.label });
    }
  }
  return out.sort((a, b) => a.approachId.localeCompare(b.approachId));
}

/** Plan-clock states, refreshed every second while `enabled`. */
export function usePlanClock(enabled: boolean, junction?: string): Phase[] {
  const [data, setData] = useState<{ js: JunctionInfo[]; lib: PlanLibrary } | null>(null);
  const [states, setStates] = useState<Phase[]>([]);
  useEffect(() => {
    if (!enabled || data) return;
    Promise.all([api<JunctionInfo[]>("/junctions"), api<PlanLibrary>("/plans/library")]).then(([js, lib]) => setData({ js, lib })).catch(() => undefined);
  }, [enabled, data]);
  useEffect(() => {
    if (!enabled || !data?.lib.available) return;
    const tick = () => setStates(planStates(junction ? data.js.filter((j) => j.id === junction) : data.js, data.lib, Date.now() / 1000));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [enabled, data, junction]);
  return enabled ? states : [];
}
