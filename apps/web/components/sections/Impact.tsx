"use client";
// Section 9: impact calculator. The formula and every assumption are on the page.
import { useId, useState } from "react";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { DEFAULT_IDLE_L_PER_H, DEFAULT_PETROL_INR, impact } from "@/lib/impact";
import { fmt, num, type Messages } from "@/lib/i18n";
import { DAY, site } from "@/lib/site";
import { Eyebrow, Reveal, Section } from "./Reveal";

const avgVehicles = Math.round(site.junctions.reduce((s, j) => s + j.survey[DAY]!.totalVeh, 0) / site.junctions.length / 1000) * 1000;

function Slider({ label, value, min, max, step, onChange, unit = "" }: { label: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void; unit?: string }) {
  const id = useId();
  return (
    <div>
      <div className="flex justify-between text-sm"><label htmlFor={id}>{label}</label><output htmlFor={id} className="font-semibold">{num(value, step < 1 ? 1 : 0)}{unit}</output></div>
      <input id={id} type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} className="mt-2 w-full accent-[var(--accent)]" />
    </div>
  );
}

export function Impact({ t }: { t: Messages }) {
  const [junctions, setJ] = useState(8);
  const [vehicles, setV] = useState(avgVehicles);
  const [seconds, setS] = useState(10);
  const [idle, setIdle] = useState(DEFAULT_IDLE_L_PER_H);
  const r = impact({ junctions, vehiclesPerJunction: vehicles, secondsSaved: seconds, idleLitresPerHour: idle });
  const out = [
    [num(r.hoursPerDay), t.impact.hours], [num(r.fuelLitres), t.impact.fuel],
    [num(r.co2Kg), t.impact.co2], [`₹${num(r.rupees)}`, t.impact.money],
  ];
  return (
    <Section id="impact">
      <div className="w-full">
        <Reveal className="max-w-2xl"><Eyebrow>{t.impact.eyebrow}</Eyebrow><h2 className="display text-4xl font-semibold sm:text-5xl">{t.impact.title}</h2></Reveal>
        <Reveal delay={0.1} className="surface mt-8 grid gap-8 rounded-3xl p-5 sm:p-7 md:grid-cols-2 [&>*]:min-w-0">
          <div className="grid gap-5">
            <Slider label={t.impact.junctions} value={junctions} min={1} max={423} step={1} onChange={setJ} />
            <Slider label={t.impact.vehicles} value={vehicles} min={10000} max={200000} step={1000} onChange={setV} />
            <Slider label={t.impact.seconds} value={seconds} min={1} max={45} step={1} onChange={setS} unit=" s" />
            <Slider label={t.impact.idle} value={idle} min={0.2} max={1.5} step={0.1} onChange={setIdle} unit=" L/h" />
          </div>
          <div>
            <SourceBadge kind="ESTIMATE" t={t.badge} />
            <dl className="mt-4 grid grid-cols-2 gap-4">
              {out.map(([v, l]) => (<div key={l}><dd className="display text-3xl font-semibold text-[var(--accent)]">{v}</dd><dt className="text-sm text-[var(--ink-2)]">{l}</dt></div>))}
            </dl>
            <details className="mt-6 text-sm" open>
              <summary className="cursor-pointer font-semibold">{t.impact.formula}</summary>
              <pre className="mt-2 overflow-x-auto rounded-xl bg-[var(--ink)]/6 p-3 text-xs leading-relaxed">{`hours/day = junctions × vehicles × seconds ÷ 3600
fuel L    = hours × idle L/h
CO₂ kg    = fuel L × 2.31`}</pre>
              <p className="mt-2 text-[var(--ink-2)]">{fmt(t.impact.assumptions, { price: DEFAULT_PETROL_INR })}</p>
            </details>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
