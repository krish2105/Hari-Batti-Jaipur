"use client";
// The signature view: the corridor as a "health barcode". Rows = junctions in road order
// (west → east, then the separate B2 Bypass pair), columns = the 24 clock hours of one survey day.
// Hovering a column highlights that hour across the whole corridor.
import Link from "next/link";
import { useState } from "react";
import { healthFill, CORRIDOR, B2_PAIR } from "@/lib/health";
import { num, useT } from "@/lib/i18n";
import type { JunctionInfo, Metrics } from "@/lib/types";

export function HealthBarcode({ metrics, byId, date, hours }: { metrics: Record<string, Metrics | null>; byId: Record<string, JunctionInfo>; date: string; hours: number[] }) {
  const { t, href } = useT();
  const [hover, setHover] = useState<number | null>(null);
  const row = (id: string) => {
    const hs = metrics[id]?.hours.filter((h) => h.survey_date === date) ?? [];
    const at = (hr: number) => hs.find((h) => h.hour === hr);
    return (
      <div key={id} role="row" className="contents">
        <Link role="rowheader" href={href(`/junction/${id}`)} className="flex min-w-0 items-center gap-2 pr-2 text-xs hover:text-[var(--accent)]">
          <span className="num font-semibold">{id}</span>
          <span className="faint hidden truncate sm:inline">{byId[id]?.name.replace(/ Junction$/, "")}</span>
        </Link>
        {Array.from({ length: 24 }, (_, hr) => {
          const h = at(hr);
          const inRange = hours.includes(hr);
          const label = h ? `${id} ${String(hr).padStart(2, "0")}:00 · ${t.metric.health} ${num(h.health)} · ${t.metric.redWait} ${num(h.red_wait_s)} s` : `${id} ${hr}:00 · —`;
          return (
            <Link role="gridcell" key={hr} href={href(`/junction/${id}?date=${date}&hour=${hr}`)} title={label} aria-label={label}
              onMouseEnter={() => setHover(hr)} onFocus={() => setHover(hr)}
              className="block h-7 rounded-[3px] transition-[opacity,transform] duration-150 hover:scale-y-110 focus-visible:scale-y-110 md:h-8"
              style={{ background: h ? healthFill(h.health) : "var(--grid)", opacity: inRange ? (hover === null || hover === hr ? 1 : 0.55) : 0.18 }} />
          );
        })}
      </div>
    );
  };
  return (
    <div className="overflow-x-auto" onMouseLeave={() => setHover(null)}>
      <div role="grid" aria-label={t.overview.barcode} className="grid min-w-[640px] items-center gap-[3px]" style={{ gridTemplateColumns: "minmax(3.2rem, 9rem) repeat(24, minmax(0, 1fr))" }}>
        <span />
        {Array.from({ length: 24 }, (_, hr) => (
          <span key={hr} aria-hidden className={`num text-center text-[10px] ${hover === hr ? "text-[var(--accent)] font-semibold" : "faint"}`}>
            {hr % 3 === 0 || hover === hr ? String(hr).padStart(2, "0") : ""}
          </span>
        ))}
        <span className="eyebrow col-span-full mt-1 !text-[10px]">{t.common.westEast}</span>
        {CORRIDOR.map(row)}
        <span className="eyebrow col-span-full mt-2 !text-[10px]">{t.common.b2}</span>
        {B2_PAIR.map(row)}
      </div>
      <div className="faint mt-3 flex flex-wrap gap-4 text-xs">
        <Legend c={healthFill(92)} l={t.overview.legendGood} />
        <Legend c={healthFill(78)} l={t.overview.legendWatch} />
        <Legend c={healthFill(60)} l={t.overview.legendAct} />
      </div>
    </div>
  );
}

function Legend({ c, l }: { c: string; l: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span aria-hidden className="inline-block h-3 w-5 rounded-[3px]" style={{ background: c }} />
      {l}
    </span>
  );
}
