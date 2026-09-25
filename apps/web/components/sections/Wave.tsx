"use client";
// Section 7: green-wave demo. Two computed rides (with / without advice) over the six corridor
// signals; averages over 60 departures so the numbers are not one lucky run.
import { useEffect, useMemo, useRef, useState } from "react";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { averageRides, ride, SPACING_M, START_BEFORE_M } from "@/lib/greenwave";
import { approachProgram, offsetOf, stateAt } from "@/lib/mockSignals";
import { num, type Messages } from "@/lib/i18n";
import { CORRIDOR, junctionById } from "@/lib/site";
import { Eyebrow, Reveal, Section } from "./Reveal";

const HEX = { RED: "#ff3b30", AMBER: "#ffb020", GREEN: "#22c55e", FLASHING_AMBER: "#ffb020" } as const;
const START_T = 1_700_000_000 + 37 * 7;

export function Wave({ t }: { t: Messages }) {
  const [withAdvice, setWithAdvice] = useState(true);
  const [clock, setClock] = useState(0);
  const [run, setRun] = useState(0);
  const avg = useMemo(() => ({ off: averageRides(false), on: averageRides(true) }), []);
  const r = useMemo(() => ride(START_T, withAdvice), [withAdvice]);
  const raf = useRef(0);
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const total = r.tripS;
    if (reduce) { setClock(total); return; }
    const start = performance.now();
    const loop = () => {
      const c = Math.min(total, ((performance.now() - start) / 1000) * 12); // 12x speed
      setClock(c);
      if (c < total) raf.current = requestAnimationFrame(loop);
    };
    raf.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf.current);
  }, [r, run]);
  const p = r.track.find((x) => x.t >= clock) ?? r.track[r.track.length - 1]!;
  const length = START_BEFORE_M + SPACING_M * 5 + 200;
  const stopsSoFar = r.track.filter((x, i) => i > 0 && x.t <= clock && x.v === 0 && r.track[i - 1]!.v > 0).length;
  return (
    <Section id="wave">
      <div className="w-full">
        <Reveal className="max-w-2xl">
          <Eyebrow>{t.wave.eyebrow}</Eyebrow>
          <h2 className="display text-4xl font-semibold sm:text-5xl">{t.wave.title}</h2>
          <p className="mt-4 text-lg text-[var(--ink-2)]">{t.wave.lede}</p>
        </Reveal>
        <Reveal delay={0.1} className="surface mt-8 rounded-3xl p-5 sm:p-7">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div role="radiogroup" className="inline-flex rounded-full border border-[var(--line)] p-1">
              {[false, true].map((on) => (
                <button key={String(on)} role="radio" aria-checked={withAdvice === on} onClick={() => setWithAdvice(on)}
                  className={`rounded-full px-4 py-2 text-sm font-semibold ${withAdvice === on ? "bg-[var(--ink)] text-[var(--bg)]" : ""}`}>
                  {on ? t.wave.with : t.wave.without}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-3">
              <SourceBadge kind="SIM" t={t.badge} />
              <button onClick={() => setRun((x) => x + 1)} className="rounded-full border border-[var(--line)] px-4 py-2 text-sm hover:border-[var(--accent)]">{t.wave.replay}</button>
            </div>
          </div>
          {/* the corridor strip */}
          <div className="relative mt-10 h-24" aria-hidden>
            <div className="absolute inset-x-0 top-1/2 h-3 -translate-y-1/2 rounded-full bg-[var(--ink)]/10" />
            {CORRIDOR.map((id, i) => {
              const x = (START_BEFORE_M + i * SPACING_M) / length;
              const s = stateAt(approachProgram(junctionById(id), true), START_T + clock + offsetOf(id));
              return (
                <div key={id} className="absolute top-0 -translate-x-1/2 text-center" style={{ left: `${x * 100}%` }}>
                  <span className="mx-auto block size-4 rounded-full" style={{ background: HEX[s.colour], boxShadow: `0 0 14px ${HEX[s.colour]}` }} />
                  <span className="mt-12 block text-[11px] text-[var(--ink-2)]">{id}</span>
                </div>
              );
            })}
            <div className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 text-2xl transition-none" style={{ left: `${(p.x / length) * 100}%` }}>🛵</div>
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <div><p className="text-sm text-[var(--ink-2)]">{withAdvice ? t.wave.with : t.wave.without}</p>
              <p className="display text-4xl font-semibold">{stopsSoFar} <span className="text-base font-normal">{t.wave.stops}</span></p>
              <p className="text-sm text-[var(--ink-2)]">{num(p.v * 3.6)} km/h</p></div>
            <div><p className="text-sm text-[var(--ink-2)]">{t.wave.without} · {t.wave.avg}</p>
              <p className="display text-2xl font-semibold">{num(avg.off.stops, 1)} {t.wave.stops} · {num(avg.off.tripS / 60, 1)} {t.wave.min}</p></div>
            <div><p className="text-sm text-[var(--ink-2)]">{t.wave.with} · {t.wave.avg}</p>
              <p className="display text-2xl font-semibold text-[var(--accent)]">{num(avg.on.stops, 1)} {t.wave.stops} · {num(avg.on.tripS / 60, 1)} {t.wave.min}</p></div>
          </div>
          <p className="mt-4 text-sm text-[var(--ink-2)]">{t.wave.tradeoff}</p>
          <p className="mt-2 text-xs text-[var(--ink-2)]">{t.wave.note}</p>
        </Reveal>
      </div>
    </Section>
  );
}
