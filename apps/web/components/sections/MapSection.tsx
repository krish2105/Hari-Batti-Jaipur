"use client";
// Section 4: the 3D map (lazy-loaded when near the viewport) + a keyboard-accessible junction list
// that mirrors it + a card with survey aggregates, health and live simulated countdowns.
import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import type { PhaseState } from "@haribatti/core";
import { LedCountdown } from "@/components/ui/LedCountdown";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { fmt, num, type Messages } from "@/lib/i18n";
import { DAY, site } from "@/lib/site";
import { healthColour } from "@/lib/health";
import { Eyebrow, Reveal, Section } from "./Reveal";

const JaipurMap = dynamic(() => import("@/components/map/JaipurMap"), { ssr: false });

export function MapSection({ t, states, dark }: { t: Messages; states: PhaseState[]; dark: boolean }) {
  const [selected, setSelected] = useState("J05");
  const [near, setNear] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const select = useCallback((id: string) => setSelected(id), []);
  useEffect(() => {
    const io = new IntersectionObserver(([e]) => e?.isIntersecting && setNear(true), { rootMargin: "600px" });
    if (ref.current) io.observe(ref.current);
    return () => io.disconnect();
  }, []);
  const j = site.junctions.find((x) => x.id === selected)!;
  const s = j.survey[DAY]!;
  const live = states.filter((x) => x.junctionId === j.id);
  return (
    <Section id="map" className="py-28">
      <Reveal className="max-w-2xl">
        <Eyebrow>{t.map.eyebrow}</Eyebrow>
        <h2 className="display text-4xl font-semibold sm:text-5xl">{t.map.title}</h2>
        <p className="mt-4 text-lg text-[var(--ink-2)]">{t.map.lede}</p>
      </Reveal>
      <div className="mt-8 grid gap-4 lg:grid-cols-[1fr_380px] [&>*]:min-w-0">
        <div ref={ref} className="surface relative h-[420px] overflow-hidden rounded-3xl sm:h-[560px]">
          {near ? <JaipurMap dark={dark} selected={selected} onSelect={select} ariaLabel={t.map.title} sharedLabel={t.map.shared} /> : <p className="p-6 text-sm text-[var(--ink-2)]">{t.map.loading}</p>}
          <p className="pointer-events-none absolute bottom-3 left-3 max-w-[70%] rounded-lg bg-[var(--bg)]/80 px-2 py-1 text-[11px] text-[var(--ink-2)]">{t.map.approx}</p>
        </div>
        <div className="surface rounded-3xl p-5" aria-live="polite">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm text-[var(--ink-2)]">{j.id}</p>
              <h3 className="display text-3xl font-semibold">{j.name}</h3>
            </div>
            <SourceBadge kind="SURVEY" t={t.badge} />
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div><dt className="text-[var(--ink-2)]">{t.map.vehicles}</dt><dd className="display text-2xl font-semibold">{num(s.totalVeh)}</dd></div>
            <div><dt className="text-[var(--ink-2)]">{t.map.pmPeak} {s.pmPeak}</dt><dd className="display text-2xl font-semibold">{num(s.pmPeakPcu)} <span className="text-sm font-normal">{t.map.pcuHr}</span></dd></div>
            <div><dt className="text-[var(--ink-2)]">{t.map.twoWheeler}</dt><dd className="display text-2xl font-semibold">{s.twoWheelerPct}%</dd></div>
            <div><dt className="text-[var(--ink-2)]">{t.map.health}</dt><dd className="display text-2xl font-semibold" style={{ color: healthColour(j.health.avg) }}>{j.health.avg}</dd>
              <dd className="text-xs text-[var(--ink-2)]">{fmt(t.map.worst, { hour: j.health.worstHour })}</dd></div>
          </dl>
          <p className="mt-3 text-xs text-[var(--ink-2)]">{t.map.healthNote}</p>
          <div className="mt-4 flex items-center justify-between">
            <h4 className="font-semibold">{t.map.approaches}</h4><SourceBadge kind="SIM" t={t.badge} />
          </div>
          <ul className="mt-2 grid gap-2">
            {live.map((a) => (
              <li key={a.approachId} className="flex items-center justify-between gap-2 border-t border-[var(--line)] pt-2 text-sm">
                <span className="truncate">{j.approaches.find((x) => a.approachId.endsWith(x.name.toLowerCase().replace(/[^a-z0-9]+/g, "-")))?.name}</span>
                <LedCountdown colour={a.colour} seconds={a.secondsRemaining} t={t.signal} size="sm" />
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-[var(--ink-2)]">{fmt(t.map.cycle, { cycle: j.plan.cycleS })} · {j.plan.source === "FIELD" ? t.badge.FIELD : t.labels.demand2}</p>
        </div>
      </div>
      <nav aria-label={t.map.listLabel} className="mt-4">
        <ul className="flex flex-wrap gap-2">
          {site.junctions.map((x) => (
            <li key={x.id}>
              <button type="button" onClick={() => setSelected(x.id)} aria-pressed={x.id === selected}
                className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm ${x.id === selected ? "border-[var(--accent)] bg-[var(--accent-2)]/15" : "border-[var(--line)] surface"}`}>
                <span className="size-2 rounded-full" style={{ background: healthColour(x.health.avg) }} aria-hidden />
                {x.id} {x.name}{x.position.lat == null && <span className="text-[11px] text-[var(--ink-2)]"> · {t.map.pending}</span>}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </Section>
  );
}
