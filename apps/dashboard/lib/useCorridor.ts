"use client";
// Loads the registry junctions and every junction's hourly metrics once, then filters on the client
// (the whole corridor is 8 junctions × 2 days × 24 hours, which is small).
import { useEffect, useMemo, useState } from "react";
import { api, useApi } from "./api";
import { ALL_JUNCTIONS } from "./health";
import type { JunctionInfo, MetricHour, Metrics } from "./types";

export type HourFilter = "all" | "am" | "pm";
export const HOURS: Record<HourFilter, number[]> = {
  all: Array.from({ length: 24 }, (_, i) => i),
  am: [8, 9, 10],
  pm: [17, 18, 19],
};

export function useCorridor() {
  const junctions = useApi<JunctionInfo[]>("/junctions");
  const [metrics, setMetrics] = useState<Record<string, Metrics | null>>({});
  const [error, setError] = useState<Error | null>(null);
  useEffect(() => {
    let alive = true;
    Promise.all(ALL_JUNCTIONS.map((id) => api<Metrics>(`/junctions/${id}/metrics`).catch(() => null)))
      .then((all) => {
        if (alive) setMetrics(Object.fromEntries(ALL_JUNCTIONS.map((id, i) => [id, all[i] ?? null])));
      })
      .catch((e) => alive && setError(e));
    return () => {
      alive = false;
    };
  }, []);
  const byId = useMemo(() => Object.fromEntries((junctions.data ?? []).map((j) => [j.id, j])), [junctions.data]);
  const loaded = Object.keys(metrics).length > 0;
  return { junctions: junctions.data, byId, metrics, loaded, error: junctions.error ?? error };
}

/** Flow-weighted summary of a set of junction-hours (same maths as the API's summarise()). */
export function summarise(rows: MetricHour[]) {
  if (!rows.length) return null;
  const w = rows.reduce((a, r) => a + (r.flow_pcu_h || 0), 0) || 1;
  const avg = (k: keyof MetricHour) => rows.reduce((a, r) => a + Number(r[k] ?? 0) * (r.flow_pcu_h || 0), 0) / w;
  const worst = rows.reduce((a, r) => (r.health < a.health ? r : a), rows[0]!);
  const approachHours = rows.flatMap((r) => r.detail?.approaches ?? []);
  return {
    health: avg("health"),
    redWaitS: avg("red_wait_s"),
    cyclesToClear: avg("cycles_to_clear"),
    starvation: avg("starvation"),
    pedRatio: avg("ped_ratio"),
    spillMin: rows.reduce((a, r) => a + (r.spill_min || 0), 0),
    flowPcu: w,
    worstHour: worst.hour,
    worstHealth: worst.health,
    overSaturated: approachHours.filter((a) => a.vc > 0.9).length,
    approachHours: approachHours.length,
  };
}

export function rowsFor(m: Metrics | null | undefined, date: string, hours: number[]) {
  return (m?.hours ?? []).filter((h) => h.survey_date === date && hours.includes(h.hour));
}
