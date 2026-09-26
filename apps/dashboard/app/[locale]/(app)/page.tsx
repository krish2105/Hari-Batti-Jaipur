"use client";
// Screen 1 — Corridor overview: KPIs, the corridor health barcode (8 junctions × 24 h), the
// schematic / map, hourly demand and the junction table. Filters: survey day and hours.
import dynamic from "next/dynamic";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useTheme } from "next-themes";
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Card, ErrorNote, Kpi, Loading, PageHead, Segmented } from "@/components/ui";
import { HealthBarcode } from "@/components/HealthBarcode";
import { CorridorSchematic } from "@/components/CorridorSchematic";
import { axis, grid, tooltip } from "@/components/charts/theme";
import { useApi } from "@/lib/api";
import { ALL_JUNCTIONS, CORRIDOR, healthColour } from "@/lib/health";
import { num, useT } from "@/lib/i18n";
import { HOURS, rowsFor, summarise, useCorridor, type HourFilter } from "@/lib/useCorridor";
import type { Kpis } from "@/lib/types";

const CorridorMap = dynamic(() => import("@/components/CorridorMap"), { ssr: false });

export default function Overview() {
  const { t, href } = useT();
  const { resolvedTheme } = useTheme();
  const [date, setDate] = useState("2026-05-11");
  const [range, setRange] = useState<HourFilter>("all");
  const [view, setView] = useState<"schematic" | "map">("schematic");
  const { junctions, byId, metrics, loaded, error } = useCorridor();
  const kpis = useApi<Kpis>(`/corridor/mansarovar/kpis?date=${date}`);
  const hours = HOURS[range];

  const per = useMemo(() => Object.fromEntries(ALL_JUNCTIONS.map((id) => [id, summarise(rowsFor(metrics[id], date, hours))])), [metrics, date, hours]);
  const health = useMemo(() => Object.fromEntries(ALL_JUNCTIONS.map((id) => [id, per[id]?.health ?? null])), [per]);
  const present = ALL_JUNCTIONS.filter((id) => per[id]);
  const avgHealth = present.length ? present.reduce((a, id) => a + per[id]!.health * per[id]!.flowPcu, 0) / present.reduce((a, id) => a + per[id]!.flowPcu, 0) : null;
  const worst = present.length ? present.reduce((a, id) => (per[id]!.health < per[a]!.health ? id : a), present[0]!) : null;
  const over = present.reduce((a, id) => a + per[id]!.overSaturated, 0);
  const cells = present.reduce((a, id) => a + per[id]!.approachHours, 0);

  // corridor demand per clock hour on both days, for the six junctions counted on both (J03–J08)
  const profile = useMemo(() => Array.from({ length: 24 }, (_, h) => {
    const sum = (d: string) => CORRIDOR.reduce((a, id) => a + (metrics[id]?.hours.find((x) => x.survey_date === d && x.hour === h)?.flow_pcu_h ?? 0), 0);
    return { hour: `${String(h).padStart(2, "0")}:00`, d11: Math.round(sum("2026-05-11")) || null, d12: Math.round(sum("2026-05-12")) || null };
  }), [metrics]);

  return (
    <>
      <PageHead title={t.overview.title} lead={t.overview.lead}>
        <Segmented label={t.common.date} value={date} onChange={setDate} options={[{ value: "2026-05-11", label: t.common.day11 }, { value: "2026-05-12", label: t.common.day12 }]} />
        <Segmented label={t.common.hours} value={range} onChange={setRange} options={[{ value: "all", label: t.common.allDay }, { value: "am", label: t.common.amPeak }, { value: "pm", label: t.common.pmPeak }]} />
      </PageHead>
      <ErrorNote error={error as never} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Kpi label={t.overview.kpiVehicles} value={num(kpis.data?.totalVehicles24h)} badge={<Badge kind="SURVEY" />} />
        <Kpi label={t.overview.kpiHealth} value={num(avgHealth, 1)} unit="/ 100" tone={healthColour(avgHealth)} badge={<Badge kind="ASSUMED" />} />
        <Kpi label={t.overview.kpiWorst} value={worst ?? "—"} hint={worst ? `${byId[worst]?.name.replace(/ Junction$/, "") ?? ""} · ${num(per[worst]?.health, 1)}` : undefined} tone={healthColour(worst ? per[worst]?.health : null)} badge={<Badge kind="ASSUMED" />} />
        <Kpi label={t.overview.kpiOver} value={num(over)} unit={`/ ${num(cells)}`} badge={<Badge kind="ASSUMED" />} />
        <Kpi label={t.overview.kpiTwoWheeler} value={num(kpis.data?.twoWheelerShareAvg, 1)} unit="%" badge={<Badge kind="SURVEY" />} />
        <Kpi label={t.overview.kpiPeak} value={kpis.data?.busiestPmPeak.junctionId ?? "—"} hint={kpis.data ? `${num(kpis.data.busiestPmPeak.pmPeakPcuHr)} PCU/h · ${kpis.data.busiestPmPeak.pmPeakStart}` : undefined} badge={<Badge kind="SURVEY" />} />
      </div>

      <Card className="mt-4" title={t.overview.barcode} badge={<span className="flex gap-1"><Badge kind="SURVEY" /><Badge kind="ASSUMED" /></span>}>
        <p className="muted mb-4 max-w-3xl text-sm">{t.overview.barcodeLead}</p>
        {loaded ? <HealthBarcode metrics={metrics} byId={byId} date={date} hours={hours} /> : <Loading />}
      </Card>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.35fr_1fr]">
        <Card title={view === "schematic" ? t.overview.schematic : t.overview.map}
          action={<Segmented label={t.overview.schematic} value={view} onChange={setView} options={[{ value: "schematic", label: t.overview.schematic }, { value: "map", label: t.overview.map }]} />}>
          {view === "schematic" ? <CorridorSchematic health={health} byId={byId} /> : junctions && <CorridorMap junctions={junctions} health={health} dark={resolvedTheme !== "light"} />}
        </Card>
        <Card title={`${t.overview.profile} · J03–J08`} badge={<Badge kind="SURVEY" />}>
          <div className="h-[280px]">
            <ResponsiveContainer>
              <AreaChart data={profile} margin={{ left: -10, right: 8, top: 8 }}>
                <defs>
                  <linearGradient id="g11" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#e8998d" stopOpacity={0.45} /><stop offset="1" stopColor="#e8998d" stopOpacity={0} /></linearGradient>
                </defs>
                <CartesianGrid {...grid} />
                <XAxis dataKey="hour" {...axis} interval={3} />
                <YAxis {...axis} width={56} tickFormatter={(v: number) => num(v)} />
                <Tooltip {...tooltip} formatter={(v) => `${num(Number(v))} PCU/h`} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Area name={t.common.day11} dataKey="d11" stroke="#e8998d" fill="url(#g11)" strokeWidth={2} />
                <Area name={t.common.day12} dataKey="d12" stroke="#7aa7ff" fill="none" strokeWidth={2} strokeDasharray="5 4" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card className="mt-4" title={t.overview.junctions} badge={<span className="flex gap-1"><Badge kind="SURVEY" /><Badge kind="ASSUMED" /></span>}>
        <div className="overflow-x-auto">
          <table className="data min-w-[760px]">
            <thead>
              <tr>
                <th>{t.common.junction}</th><th>{t.metric.health}</th><th>{t.metric.redWait}</th><th>{t.metric.starvation}</th>
                <th>{t.metric.ped}</th><th>{t.metric.spill}</th><th>{t.metric.flow}</th><th>{t.junction.worstHour}</th><th />
              </tr>
            </thead>
            <tbody>
              {ALL_JUNCTIONS.map((id) => {
                const s = per[id];
                return (
                  <tr key={id}>
                    <td className="whitespace-nowrap"><span className="num font-semibold">{id}</span> <span className="muted">{byId[id]?.name.replace(/ Junction$/, "")}</span></td>
                    <td className="num font-semibold" style={{ color: healthColour(s?.health) }}>{num(s?.health, 1)}</td>
                    <td className="num">{num(s?.redWaitS)} s</td>
                    <td className="num" style={{ color: s && s.starvation < 0.8 ? "#ff3b30" : undefined }}>{num(s?.starvation, 2)}</td>
                    <td className="num" style={{ color: s && s.pedRatio < 1 ? "#ffb020" : undefined }}>{num(s?.pedRatio, 2)}</td>
                    <td className="num">{num(s?.spillMin)} {t.common.min}</td>
                    <td className="num">{num(s?.flowPcu)} PCU</td>
                    <td className="num">{s ? `${String(s.worstHour).padStart(2, "0")}:00` : "—"}</td>
                    <td><Link className="text-[var(--accent)] underline-offset-2 hover:underline" href={href(`/junction/${id}?date=${date}`)}>{t.overview.open} →</Link></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
