"use client";
// Screen 3 — Junction detail: the five metrics at a chosen hour, every approach, the phase ring of
// the plan in force, a 24-hour approach heatmap, hourly demand on both survey days, live phases
// from the simulator feed and the camera slot (CV results appear once services/cv has run).
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Card, ErrorNote, Kpi, Led, Loading, PageHead, Segmented, SourceBadges } from "@/components/ui";
import { PhaseRing, stagesFrom } from "@/components/PhaseRing";
import { NotesPanel } from "@/components/pilot";
import { axis, grid, tooltip } from "@/components/charts/theme";
import { useApi } from "@/lib/api";
import { DEFAULT_TENANT } from "@/lib/pilot";
import { healthColour, healthFill, SIGNAL_HEX } from "@/lib/health";
import { useLive } from "@/lib/live";
import { fmt, num, useT } from "@/lib/i18n";
import type { CvEval, JunctionInfo, Metrics } from "@/lib/types";

const DATES = ["2026-05-11", "2026-05-12"] as const;
const hh = (h: number) => `${String(h).padStart(2, "0")}:00`;

function JunctionDetail() {
  const { t, href } = useT();
  const { id: raw } = useParams<{ id: string }>();
  const id = (raw ?? "").toUpperCase();
  const sp = useSearchParams();
  const router = useRouter();
  const date = sp.get("date") === "2026-05-12" ? "2026-05-12" : "2026-05-11";
  const hour = Math.min(23, Math.max(0, Number(sp.get("hour") ?? 18) || 0));
  const setQuery = (d: string, h: number) => router.replace(href(`/junction/${id}?date=${d}&hour=${h}`), { scroll: false });

  const info = useApi<JunctionInfo>(`/junctions/${id}`);
  const metrics = useApi<Metrics>(`/junctions/${id}/metrics`);
  const cv = useApi<CvEval>("/analytics/cv");
  const { states, feed } = useLive(id);

  const j = info.data;
  const days = useMemo(() => DATES.filter((d) => metrics.data?.hours.some((h) => h.survey_date === d)), [metrics.data]);
  const dayHours = useMemo(() => (metrics.data?.hours ?? []).filter((h) => h.survey_date === date), [metrics.data, date]);
  const at = dayHours.find((h) => h.hour === hour);
  const approaches = j?.approaches ?? [];
  const lanes = Object.fromEntries(approaches.map((a) => [a.name, a]));
  const stages = at ? stagesFrom(at.detail.green_s, approaches) : [];
  const names = Object.fromEntries(approaches.map((a) => [a.id, a.name]));

  // hourly demand on both days (index of hourlyPcu = clock hour)
  const demand = useMemo(() => Array.from({ length: 24 }, (_, h) => ({
    hour: hh(h),
    d11: j?.hourlyPcu?.["2026-05-11"]?.[h] ?? null,
    d12: j?.hourlyPcu?.["2026-05-12"]?.[h] ?? null,
  })), [j]);

  const cvHere = cv.data?.available ? (cv.data.videos ?? []).filter((v) => v.junctionId === id) : [];

  if (info.error?.status === 404) {
    return (
      <Card>
        <p className="text-sm">{info.error.message}</p>
        <Link className="btn mt-3" href={href("/")}>← {t.junction.back}</Link>
      </Card>
    );
  }

  return (
    <>
      <Link href={href("/")} className="no-print faint mb-3 inline-block text-sm hover:text-[var(--accent)]">← {t.junction.back}</Link>
      <PageHead title={j ? `${id} · ${j.name}` : id} lead={j ? `${j.tmcCode ?? "—"} · ${t.junction.position}: ${j.positionNote}` : undefined}>
        {days.length > 1 && (
          <Segmented label={t.common.date} value={date} onChange={(d) => setQuery(d, hour)}
            options={[{ value: "2026-05-11", label: t.common.day11 }, { value: "2026-05-12", label: t.common.day12 }]} />
        )}
        <label className="flex items-center gap-2 text-sm">
          <span className="muted">{t.junction.pickHour}</span>
          <select className="field num" value={hour} onChange={(e) => setQuery(date, Number(e.target.value))}>
            {Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{hh(h)}</option>)}
          </select>
        </label>
      </PageHead>
      <ErrorNote error={info.error ?? metrics.error} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Kpi label={t.metric.health} value={num(at?.health, 1)} unit="/ 100" tone={healthColour(at?.health)} badge={<Badge kind="ASSUMED" />} hint={t.metric.healthHelp} />
        <Kpi label={t.metric.redWait} value={num(at?.red_wait_s)} unit={t.common.sec} badge={<Badge kind="ASSUMED" />} />
        <Kpi label={t.metric.cycles} value={num(at?.cycles_to_clear, 2)} badge={<Badge kind="ASSUMED" />} />
        <Kpi label={t.metric.starvation} value={num(at?.starvation, 2)} tone={at && at.starvation < 0.8 ? "#ff3b30" : undefined} badge={<Badge kind="ASSUMED" />} />
        <Kpi label={t.metric.ped} value={num(at?.ped_ratio, 2)} tone={at && at.ped_ratio < 1 ? "#ffb020" : undefined} badge={<Badge kind="ASSUMED" />} />
        <Kpi label={t.metric.flow} value={num(at?.flow_pcu_h)} unit={t.common.pcuH} badge={<Badge kind="SURVEY" />} />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <Card insight={`junction.${id}.approaches`} title={fmt(t.junction.approaches, { hour: hh(hour) })} badge={<SourceBadges source={metrics.data?.source} />}>
          {!metrics.data && !metrics.error ? <Loading /> : !at ? <p className="muted text-sm">{t.common.empty}</p> : (
            <div className="overflow-x-auto">
              <table className="data min-w-[640px]">
                <thead>
                  <tr>
                    <th>{t.common.approach}</th><th>{t.junction.lanes}</th><th>{t.common.vc}</th><th>{t.junction.green}</th>
                    <th>{t.metric.redWait}</th><th>{t.metric.starvation}</th><th>{t.metric.ped}</th><th>{t.metric.flow}</th><th>{t.metric.health}</th>
                  </tr>
                </thead>
                <tbody>
                  {at.detail.approaches.map((a) => (
                    <tr key={a.approach}>
                      <td>{a.approach}{lanes[a.approach]?.isMain && <span className="faint text-xs"> · {t.junction.mainRoad}</span>}</td>
                      <td className="num">{lanes[a.approach]?.lanes ?? "—"}<span className="faint text-[10px]"> {lanes[a.approach]?.lanesSource === "FIELD" ? "" : "*"}</span></td>
                      <td className="num" style={{ color: a.vc > 0.9 ? "#ff3b30" : undefined }}>{num(a.vc, 2)}</td>
                      <td className="num">{num(at.detail.green_s[a.approach])} s</td>
                      <td className="num">{num(a.red_wait_s)} s</td>
                      <td className="num" style={{ color: a.starvation < 0.8 ? "#ff3b30" : undefined }}>{num(a.starvation, 2)}</td>
                      <td className="num" style={{ color: a.ped_ratio < 1 ? "#ffb020" : undefined }}>{num(a.ped_ratio, 2)}</td>
                      <td className="num">{num(a.flow_pcu_h)}</td>
                      <td className="num font-semibold" style={{ color: healthColour(a.health) }}>{num(a.health)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="faint mt-2 text-xs">* {t.junction.lanesAssumed} · Y = {num(at.detail.Y, 2)}{at.detail.oversaturated ? ` · ${t.junction.oversaturated}` : ""}</p>
            </div>
          )}
        </Card>

        <Card title={t.junction.ring} badge={<Badge kind="ASSUMED" />}>
          {at ? (
            <>
              <PhaseRing cycleS={at.detail.cycle_s} stages={stages} label={t.junction.ring} />
              <p className="faint mt-3 text-xs">{fmt(t.junction.ringNote, { cycle: at.detail.cycle_s })} {metrics.data?.timingLabel}</p>
            </>
          ) : <Loading />}
        </Card>
      </div>

      <Card className="mt-4" insight={`junction.${id}.heatmap`} title={t.junction.heatmap} badge={<span className="flex gap-1"><Badge kind="SURVEY" /><Badge kind="ASSUMED" /></span>}>
        {dayHours.length ? <ApproachHeatmap id={id} hours={dayHours} hour={hour} onPick={(h) => setQuery(date, h)} /> : <Loading />}
      </Card>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <Card insight={`junction.${id}.demand`} title={t.junction.demand} badge={<Badge kind="SURVEY" />}>
          <div className="h-[260px]">
            <ResponsiveContainer>
              <LineChart data={demand} margin={{ left: -10, right: 8, top: 8 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="hour" {...axis} interval={3} />
                <YAxis {...axis} width={56} tickFormatter={(v: number) => num(v)} />
                <Tooltip {...tooltip} formatter={(v) => `${num(Number(v))} ${t.common.pcuH}`} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line name={t.common.day11} dataKey="d11" stroke="#e8998d" strokeWidth={2} dot={false} />
                <Line name={t.common.day12} dataKey="d12" stroke="#7aa7ff" strokeWidth={2} strokeDasharray="5 4" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="faint mt-2 text-xs">
            {(j?.survey ?? []).map((s) => `${s.surveyDate}: ${num(s.totalVeh)} ${t.junction.vehicles} · ${fmt(t.junction.peaks, { am: `${s.amPeakStart} (${num(s.amPeakPcuHr)})`, pm: `${s.pmPeakStart} (${num(s.pmPeakPcuHr)})` })}`).join(" | ")}
          </p>
        </Card>

        <Card title={t.junction.live} badge={states[0] ? <Badge kind={states[0].source === "ITMS" ? "ITMS" : states[0].source === "CROWD" ? "CROWD" : "SIM"} /> : undefined}>
          {states.length === 0 ? (
            <p className="muted text-sm">{feed === "down" ? t.offline.title : t.live.noFeed}</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {feed === "planClock" && <li className="faint text-xs">{t.live.planClock}</li>}
              {states.map((s) => (
                <li key={s.approachId} className="panel-2 flex items-center justify-between gap-3 px-3 py-2">
                  <span className="flex min-w-0 items-center gap-2 text-sm">
                    <span aria-hidden className="size-3 shrink-0 rounded-full" style={{ background: SIGNAL_HEX[s.colour], boxShadow: `0 0 8px ${SIGNAL_HEX[s.colour]}` }} />
                    <span className="truncate">{names[s.approachId] ?? s.approachId}</span>
                    <span className="faint text-xs">{t.live.confidence} {num(s.confidence * 100)}%</span>
                  </span>
                  <Led colour={s.colour} seconds={s.secondsRemaining} />
                </li>
              ))}
              {states[0]?.simClock && <li className="faint num text-xs">{t.live.simClock}: {states[0].simClock}</li>}
            </ul>
          )}
        </Card>
      </div>

      <Card className="mt-4" title={t.junction.camera} badge={cvHere.length ? <Badge kind="FIELD" /> : undefined}>
        {cvHere.length ? (
          <ul className="text-sm">
            {cvHere.map((v) => <li key={v.clip}>{v.clip}: {num(v.counts)} {t.junction.vehicles} <SourceBadges source={v.source} /></li>)}
          </ul>
        ) : (
          <div className="flex items-center gap-4">
            <span aria-hidden className="grid aspect-video w-40 shrink-0 place-items-center rounded-lg border border-dashed border-[var(--line)] text-[var(--ink-3)]">
              <svg viewBox="0 0 24 24" className="size-8" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 7h12v10H3zM15 10l6-3v10l-6-3" /></svg>
            </span>
            <p className="muted text-sm">{t.junction.cameraNote}</p>
          </div>
        )}
      </Card>

      {/* officer notes and pins for this junction (the Jaipur police pilot tenant) */}
      <div className="mt-4">
        <NotesPanel tenantId={DEFAULT_TENANT} sites={[]} siteId={id} approaches={j?.approaches.map((a) => a.name) ?? []} />
      </div>
    </>
  );
}

/** Approach × clock-hour grid coloured by approach Health; click a column to pick that hour. */
function ApproachHeatmap({ id, hours, hour, onPick }: { id: string; hours: Metrics["hours"]; hour: number; onPick: (h: number) => void }) {
  const { t } = useT();
  const names = [...new Set(hours.flatMap((h) => h.detail.approaches.map((a) => a.approach)))];
  const cell = (name: string, hr: number) => hours.find((h) => h.hour === hr)?.detail.approaches.find((a) => a.approach === name);
  return (
    <div className="overflow-x-auto">
      <div role="grid" aria-label={t.junction.heatmap} className="grid min-w-[640px] items-center gap-[3px]" style={{ gridTemplateColumns: "minmax(6rem, 11rem) repeat(24, minmax(0, 1fr))" }}>
        <span />
        {Array.from({ length: 24 }, (_, hr) => (
          <span key={hr} aria-hidden className={`num text-center text-[10px] ${hr === hour ? "font-semibold text-[var(--accent)]" : "faint"}`}>{hr % 3 === 0 || hr === hour ? String(hr).padStart(2, "0") : ""}</span>
        ))}
        {names.map((name) => (
          <div key={name} role="row" className="contents">
            <span role="rowheader" className="truncate pr-2 text-xs">{name}</span>
            {Array.from({ length: 24 }, (_, hr) => {
              const a = cell(name, hr);
              const label = a ? `${id} ${name} ${hh(hr)} · ${t.metric.health} ${num(a.health)} · ${t.common.vc} ${num(a.vc, 2)} · ${t.metric.redWait} ${num(a.red_wait_s)} s` : `${name} ${hh(hr)} · —`;
              return (
                <button key={hr} type="button" role="gridcell" title={label} aria-label={label} onClick={() => onPick(hr)}
                  className={`h-7 rounded-[3px] ${hr === hour ? "ring-2 ring-[var(--accent)]" : ""}`}
                  style={{ background: a ? healthFill(a.health) : "var(--grid)" }} />
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <JunctionDetail />
    </Suspense>
  );
}
