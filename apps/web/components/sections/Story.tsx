"use client";
// Sections 1–3, 5, 6, 8: the scroll story text over the 3D city.
import { useEffect, useState } from "react";
import type { PhaseState } from "@haribatti/core";
import { LedCountdown } from "@/components/ui/LedCountdown";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { fmt, num, type Messages } from "@/lib/i18n";
import { DAY, junctionById, site } from "@/lib/site";
import { Eyebrow, Reveal, Section } from "./Reveal";

export function Hero({ t, states }: { t: Messages; states: PhaseState[] }) {
  const j = junctionById("J05");
  const s = states.find((x) => x.approachId === "J05-mansarover-metro");
  return (
    <Section id="hero" className="justify-end pb-16 sm:justify-center">
      <div className="grid w-full gap-10 md:grid-cols-[1.4fr_1fr] md:items-end [&>*]:min-w-0">
        {/* no fade-in on the hero: it is the first paint (LCP) and must not wait for JavaScript */}
        <div>
          <Eyebrow>{t.hero.eyebrow}</Eyebrow>
          <h1 className="display text-[clamp(2.6rem,7.5vw,6.2rem)] leading-[0.95] font-semibold">
            <span className="block">{t.hero.title1}</span>
            <span className="block text-[var(--accent)] italic">{t.hero.title2}</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg text-[var(--ink-2)]">{t.hero.lede}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a href="#map" className="rounded-full bg-[var(--ink)] px-6 py-3 font-semibold text-[var(--bg)] hover:opacity-90">{t.hero.ctaMap}</a>
            <a href="#wave" className="rounded-full border border-[var(--line)] px-6 py-3 font-semibold surface hover:border-[var(--accent)]">{t.hero.ctaDemo}</a>
          </div>
        </div>
        <Reveal delay={0.15} className="justify-self-start md:justify-self-end">
          {/* glass, not a solid card: the live street behind the countdown must stay visible */}
          <div className="glass w-fit max-w-full rounded-3xl p-5">
            <div className="mb-3 flex items-center justify-between gap-4">
              <span className="glass-text text-sm font-medium text-[var(--ink)]">{fmt(t.hero.liveLabel, { name: `${j.id} ${j.name}`, approach: "Mansarover Metro" })}</span>
              <SourceBadge kind="SIM" t={t.badge} />
            </div>
            {s && <LedCountdown colour={s.colour} seconds={s.secondsRemaining} t={t.signal} size="xl" />}
            <p className="glass-text mt-2 text-xs font-medium text-[var(--ink)]">{t.labels.demand2}</p>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}

export function Wait({ t }: { t: Messages }) {
  const PER_SECOND = (750_000 * 121) / (365 * 24 * 3600); // ≈ 2.88 hours lost per second (estimate)
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    const start = performance.now();
    const id = setInterval(() => setSecs((performance.now() - start) / 1000), 250);
    return () => clearInterval(id);
  }, []);
  const c = site.corridor;
  const busiest = junctionById(c.busiestPmPeak);
  return (
    <Section id="wait">
      <div className="grid w-full gap-8 md:grid-cols-2">
        <Reveal className="surface rounded-3xl p-6 sm:p-8">
          <Eyebrow>{t.wait.eyebrow}</Eyebrow>
          <h2 className="display text-3xl font-semibold sm:text-4xl">{t.wait.title}</h2>
          <p className="led mt-6 text-[clamp(3rem,9vw,5.5rem)] leading-none text-[var(--accent)]" aria-live="off">{num(secs * PER_SECOND, 1)}</p>
          <p className="mt-1 text-sm font-semibold">{t.wait.hours} <SourceBadge kind="ESTIMATE" t={t.badge} className="ml-2 align-middle" /></p>
          <p className="mt-4 text-sm text-[var(--ink-2)]">{t.wait.method}</p>
        </Reveal>
        <Reveal delay={0.1} className="surface self-end rounded-3xl p-6 sm:p-8">
          <SourceBadge kind="SURVEY" t={t.badge} />
          <p className="mt-4 text-xl">{fmt(t.wait.survey, { total: num(c.totalVeh) })}</p>
          <p className="mt-3 text-[var(--ink-2)]">{fmt(t.wait.twoWheelers, { min: c.twoWheelerPctRange[0], max: c.twoWheelerPctRange[1] })}</p>
          <p className="mt-3 text-[var(--ink-2)]">{fmt(t.wait.peak, { pcu: num(busiest.survey[DAY]!.pmPeakPcu), name: `${busiest.id} ${busiest.name}` })}</p>
        </Reveal>
      </div>
    </Section>
  );
}

export function Squeeze({ t }: { t: Messages }) {
  const c = site.corridor;
  const stats = [
    { v: fmt(t.squeeze.stat1, { n: c.vcOver09, total: c.vcRows }), l: t.squeeze.stat1Label, n: t.squeeze.stat1Note, b: "ASSUMED" as const },
    { v: t.squeeze.stat2, l: t.squeeze.stat2Label, n: t.squeeze.stat2Note, b: "SURVEY" as const },
    { v: t.squeeze.stat3, l: t.squeeze.stat3Label, n: t.squeeze.stat3Note, b: "ESTIMATE" as const },
  ];
  return (
    <Section id="squeeze">
      <div className="w-full">
        <Reveal className="max-w-2xl">
          <Eyebrow>{t.squeeze.eyebrow}</Eyebrow>
          <h2 className="display text-4xl font-semibold sm:text-5xl">{t.squeeze.title}</h2>
          <p className="mt-5 text-lg text-[var(--ink-2)]">{t.squeeze.p1}</p>
        </Reveal>
        <div className="mt-10 grid gap-4 sm:grid-cols-3">
          {stats.map((s, i) => (
            <Reveal key={s.l} delay={i * 0.08} className="surface rounded-2xl p-5">
              <SourceBadge kind={s.b} t={t.badge} />
              <p className="display mt-3 text-4xl font-semibold text-[var(--accent)]">{s.v}</p>
              <p className="mt-2 font-semibold">{s.l}</p>
              <p className="mt-2 text-sm text-[var(--ink-2)]">{s.n}</p>
            </Reveal>
          ))}
        </div>
        <Reveal delay={0.2}><p className="mt-6 text-[var(--ink-2)]">{t.squeeze.ped}</p></Reveal>
      </div>
    </Section>
  );
}

export function Itms({ t }: { t: Messages }) {
  return (
    <Section id="itms">
      <Reveal className="surface max-w-2xl rounded-3xl p-6 sm:p-8">
        <Eyebrow>{t.itms.eyebrow}</Eyebrow>
        <h2 className="display text-4xl font-semibold">{t.itms.title}</h2>
        <div className="mt-6 flex flex-wrap gap-6">
          <div><p className="display text-5xl font-semibold text-[var(--color-itms-blue)]">8–45 s</p><p className="text-sm text-[var(--ink-2)]">Rambagh Circle</p></div>
          <div><p className="display text-5xl font-semibold text-[var(--color-itms-blue)]">253 / 423</p><p className="text-sm text-[var(--ink-2)]">AI-ITMS</p></div>
        </div>
        <p className="mt-6 text-lg">{t.itms.p1}</p>
        <p className="mt-4 text-[var(--ink-2)]">{t.itms.p2}</p>
        <p className="mt-6 text-xs text-[var(--ink-2)]">{t.itms.credit}</p>
      </Reveal>
    </Section>
  );
}

export function Solution({ t, states }: { t: Messages; states: PhaseState[] }) {
  const s = states.find((x) => x.approachId === "J06-mansarover-metro");
  const cards = [
    { h: t.solution.app, p: t.solution.appText },
    { h: t.solution.command, p: t.solution.commandText },
    { h: t.solution.reports, p: t.solution.reportsText },
  ];
  return (
    <Section id="solution">
      <div className="grid w-full items-center gap-10 md:grid-cols-[1fr_300px]">
        <div>
          <Reveal>
            <Eyebrow>{t.solution.eyebrow}</Eyebrow>
            <h2 className="display text-4xl font-semibold sm:text-5xl">{t.solution.title}</h2>
          </Reveal>
          <div className="mt-8 grid gap-4">
            {cards.map((c, i) => (
              <Reveal key={c.h} delay={i * 0.08} className="surface rounded-2xl p-5">
                <h3 className="display text-2xl font-semibold">{c.h}</h3>
                <p className="mt-2 text-[var(--ink-2)]">{c.p}</p>
              </Reveal>
            ))}
          </div>
        </div>
        <Reveal delay={0.15} className="mx-auto w-full max-w-[300px]">
          <div className="rounded-[2.5rem] border-8 border-[#0b1220] bg-[#0b1220] p-4 text-[#f6e7e2] shadow-2xl">
            <div className="mx-auto mb-4 h-1.5 w-16 rounded-full bg-white/15" />
            <p className="text-xs uppercase tracking-widest text-white/60">{t.solution.phone} · J06 VT Road</p>
            {s && <div className="mt-3"><LedCountdown colour={s.colour} seconds={s.secondsRemaining} t={t.signal} /></div>}
            <p className="mt-4 rounded-xl bg-white/8 p-3 text-lg font-semibold">
              {s?.colour === "GREEN" ? fmt(t.solution.advice, { kmh: 30 }) : t.solution.prepare}
            </p>
            <div className="mt-4 flex justify-between text-xs text-white/60"><span>J07 Rajat Path</span><span>J08 Bhrigu Path</span></div>
            <div className="mt-3"><SourceBadge kind="SIM" t={t.badge} /></div>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}

export function Ai({ t }: { t: Messages }) {
  const items = [
    [t.ai.predict, t.ai.predictText], [t.ai.vision, t.ai.visionText], [t.ai.audit, t.ai.auditText],
    [t.ai.copilot, t.ai.copilotText], [t.ai.events, t.ai.eventsText],
  ] as const;
  return (
    <Section id="ai">
      <div className="w-full">
        <Reveal><Eyebrow>{t.ai.eyebrow}</Eyebrow><h2 className="display max-w-2xl text-4xl font-semibold sm:text-5xl">{t.ai.title}</h2></Reveal>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map(([h, p], i) => (
            <Reveal key={h} delay={i * 0.06} className={`surface rounded-2xl p-5 ${i === 3 ? "lg:col-span-2" : ""}`}>
              <h3 className="display text-2xl font-semibold">{h}</h3>
              <p className="mt-2 text-[var(--ink-2)]">{p}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </Section>
  );
}
