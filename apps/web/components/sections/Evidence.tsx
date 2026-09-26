"use client";
// Section "Evidence": what the models actually show, with baselines, held-out data and source labels.
// Four tabs (digital-twin calibration, signal timing, forecasts, computer vision), each with small
// interactive charts. Numbers come from public/data/results.json (aggregates only).
import { useState } from "react";
import { Bars, Meter, Scatter, Tabs, type Bar } from "@/components/ui/Charts";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { fmt, num, type Messages } from "@/lib/i18n";
import { results, type Controller } from "@/lib/results";
import { Eyebrow, Reveal, Section } from "./Reveal";

type Tab = "calib" | "timing" | "forecast" | "vision";
const pct = (v: number | null | undefined, d = 0) => (v === null || v === undefined ? "—" : `${num(v * 100, d)}%`);

export function Evidence({ t }: { t: Messages }) {
  const e = t.evidence;
  const [tab, setTab] = useState<Tab>("calib");
  return (
    <Section id="evidence">
      <Reveal className="max-w-3xl">
        <Eyebrow>{e.eyebrow}</Eyebrow>
        <h2 className="display text-4xl font-semibold sm:text-5xl">{e.title}</h2>
        <p className="legible mt-4 text-lg text-[var(--ink-2)]">{e.lede}</p>
      </Reveal>
      <div className="mt-8">
        <Tabs label={e.title} value={tab} onChange={setTab}
          options={[{ value: "calib", label: e.tabs.calib }, { value: "timing", label: e.tabs.timing }, { value: "forecast", label: e.tabs.forecast }, { value: "vision", label: e.tabs.vision }]} />
      </div>
      <div role="tabpanel" className="mt-5">
        {tab === "calib" && <Calibration t={t} />}
        {tab === "timing" && <Timing t={t} />}
        {tab === "forecast" && <Forecast t={t} />}
        {tab === "vision" && <Vision t={t} />}
      </div>
    </Section>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`surface min-w-0 rounded-3xl p-5 sm:p-6 ${className}`}>{children}</div>;
}

function Kpi({ label, value, hint, badge, tone }: { label: string; value: string; hint?: string; badge: React.ReactNode; tone?: "bad" | "good" }) {
  return (
    <div className="surface flex min-w-0 flex-col gap-1.5 rounded-2xl p-4">
      <span className="text-xs font-semibold uppercase tracking-wider text-[var(--ink-2)]">{label}</span>
      <span className={`led text-3xl leading-none ${tone === "bad" ? "text-[#d9352b] dark:text-[#ff6b61]" : tone === "good" ? "text-[#1f9d4d] dark:text-[#4ade80]" : ""}`}>{value}</span>
      <span className="flex flex-wrap items-center gap-2 text-xs text-[var(--ink-2)]">{badge}{hint}</span>
    </div>
  );
}

function Pending({ t }: { t: Messages }) {
  return <Card><p className="text-[var(--ink-2)]">{t.evidence.pending}</p></Card>;
}

function Calibration({ t }: { t: Messages }) {
  const c = results.calibration;
  const e = t.evidence.calib;
  if (!c) return <Pending t={t} />;
  const names = e.variants as Record<string, string>;
  const pass = (v: number | null) => (v !== null && v >= c.target ? "good" : "bad") as "good" | "bad";
  const best = c.trials.reduce((a, b) => (b.cal > a.cal ? b : a), c.trials[0]!);
  return (
    <div className="grid gap-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label={e.cal} value={pct(c.calibration)} tone={pass(c.calibration)} hint={fmt(e.target, { n: c.target * 100 })} badge={<SourceBadge kind="SIM" t={t.badge} />} />
        <Kpi label={e.val} value={pct(c.validation)} tone={pass(c.validation)} hint={fmt(e.target, { n: c.target * 100 })} badge={<SourceBadge kind="SIM" t={t.badge} />} />
        <Kpi label={e.unserved} value={pct(c.unserved)} tone={(c.unserved ?? 1) < c.unservedTarget ? "good" : "bad"} hint={fmt(e.target, { n: "< 5" })} badge={<SourceBadge kind="SIM" t={t.badge} />} />
        <Kpi label={e.trials} value={num(c.trialsRun)} hint={e.search} badge={<SourceBadge kind="SIM" t={t.badge} />} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="display text-2xl font-semibold">{e.variantsTitle}</h3>
          <p className="mt-1 mb-4 text-sm text-[var(--ink-2)]">{e.geh}</p>
          <Bars format={(v) => pct(v)} max={1} refValue={c.target} refLabel={fmt(e.target, { n: c.target * 100 })}
            rows={c.variants.map((v): Bar => ({ key: v.id, label: `${v.id} · ${names[v.id] ?? v.label}`, value: v.cal, strong: v.cal === Math.max(...c.variants.map((x) => x.cal)),
              note: `${e.val}: ${pct(v.val)} · ${e.unserved}: ${pct(v.unserved)}` }))} />
        </Card>
        <Card>
          <h3 className="display text-2xl font-semibold">{e.trialsTitle}</h3>
          <Scatter xLabel={e.scatterX} yLabel={e.scatterY} target={c.target} caption={e.scatterNote}
            points={c.trials.map((p) => ({ key: String(p.trial), x: p.cal, y: p.val, r: 4 + 10 * Math.min(1, p.unserved), strong: p.trial === best.trial,
              label: fmt(e.trialPoint, { n: p.trial, lanes: p.lanes, cal: pct(p.cal), val: pct(p.val), u: pct(p.unserved) }) }))} />
        </Card>
      </div>
      <p className="text-sm text-[var(--ink-2)]">{e.why} {c.saturationPcu ? fmt(e.satflow, { n: num(c.saturationPcu) }) : ""}</p>
    </div>
  );
}

const METRICS = ["travelTimeS", "waitingTimeS", "stops", "co2PerTripG", "queueVeh"] as const;
type Metric = (typeof METRICS)[number];

function Timing({ t }: { t: Messages }) {
  const o = results.optimisation;
  const e = t.evidence.timing;
  const [m, setM] = useState<Metric>("travelTimeS");
  if (!o) return <Pending t={t} />;
  const names = e.ctrl as Record<string, string>;
  const digits = m === "stops" ? 2 : 0;
  const sorted = [...o.controllers].sort((a: Controller, b: Controller) => a[m].mean - b[m].mean);
  const best = sorted[0]!;
  const gw = o.greenWave;
  return (
    <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="display text-2xl font-semibold">{e.title}</h3>
          <SourceBadge kind="SIM" t={t.badge} />
        </div>
        <p className="mt-1 text-sm text-[var(--ink-2)]">{fmt(e.held, { day: o.evalDay, window: o.window, seeds: o.seeds })}</p>
        <div className="my-4"><Tabs label={e.metric} value={m} onChange={setM} options={METRICS.map((k) => ({ value: k, label: (e.metrics as Record<string, string>)[k]! }))} /></div>
        <Bars format={(v) => num(v, digits)} lowerIsBetter
          rows={sorted.map((r): Bar => ({ key: r.id, label: names[r.id] ?? r.label, value: r[m].mean, ci: r[m].ci95, strong: r.id === best.id, muted: r.id === "even",
            note: `${(e.metrics as Record<string, string>).travelTimeS}: ${num(r.travelTimeS.mean)} s · ${(e.metrics as Record<string, string>).stops}: ${num(r.stops.mean, 2)} · ${e.unserved}: ${num(r.unservedVeh.mean)}` }))} />
        <p className="mt-3 text-sm"><b>{fmt(e.best, { name: names[best.id] ?? best.label })}</b> · {e.lower}</p>
      </Card>
      <Card>
        <h3 className="display text-2xl font-semibold">{e.wave}</h3>
        {gw ? (
          <>
            <p className="mt-1 mb-4 text-sm text-[var(--ink-2)]">{fmt(e.waveNote, { c: gw.cycleS, v: gw.speedKmh, s: gw.spacingM })}</p>
            <Bars format={(v) => `${num(v)} s`} max={gw.cycleS}
              rows={[
                { key: "e0", label: `${e.east} · ${e.zero}`, value: gw.bandwidthZeroOffsetsS.eastbound, muted: true },
                { key: "e1", label: `${e.east} · ${e.with}`, value: gw.bandwidthS.eastbound, strong: true },
                { key: "w0", label: `${e.west} · ${e.zero}`, value: gw.bandwidthZeroOffsetsS.westbound, muted: true },
                { key: "w1", label: `${e.west} · ${e.with}`, value: gw.bandwidthS.westbound, strong: true },
              ]} />
            <p className="mt-3 text-xs text-[var(--ink-2)]">{e.band}</p>
            <table className="mt-4 w-full text-sm">
              <thead><tr className="text-left text-xs text-[var(--ink-2)]"><th className="py-1 font-semibold">{e.junction}</th><th className="font-semibold">{e.green}</th><th className="font-semibold">{e.offset}</th></tr></thead>
              <tbody>{gw.junctions.map((j) => <tr key={j.id} className="border-t border-[var(--line)]"><td className="py-1">{j.id}</td><td className="led">{num(j.greenS)} s</td><td className="led">{num(j.offsetS)} s</td></tr>)}</tbody>
            </table>
          </>
        ) : <p className="mt-2 text-[var(--ink-2)]">{t.evidence.pending}</p>}
        <p className="mt-4 text-xs text-[var(--ink-2)]">{e.recommend}</p>
      </Card>
    </div>
  );
}

function Forecast({ t }: { t: Messages }) {
  const f = results.forecast;
  const e = t.evidence.forecast;
  const [which, setWhich] = useState<"real" | "sim">("real");
  if (!f) return <Pending t={t} />;
  const b = f[which];
  const names = e.models as Record<string, string>;
  const best = Math.min(...b.models.map((x) => x.wape));
  return (
    <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="display text-2xl font-semibold">{e.title}</h3>
          <SourceBadge kind={which === "real" ? "SURVEY" : "SIM"} t={t.badge} />
        </div>
        <div className="my-4"><Tabs label={e.title} value={which} onChange={setWhich} options={[{ value: "real", label: e.real }, { value: "sim", label: e.sim }]} /></div>
        <p className="mb-3 text-sm text-[var(--ink-2)]">{fmt(e.split, { train: num(b.nTrain), test: num(b.nTest) })}</p>
        <Bars format={(v) => pct(v, 1)}
          rows={b.models.map((x): Bar => ({ key: x.id, label: `${names[x.id] ?? x.label}${x.isBaseline ? ` (${e.baseline})` : ""}`, value: x.wape, strong: x.wape === best, muted: x.isBaseline,
            note: `MAE ${num(x.mae, 1)} · RMSE ${num(x.rmse, 1)} ${e.perSlot}` }))} />
        <p className="mt-3 text-xs text-[var(--ink-2)]">{e.wape} {e.honest}</p>
        {which === "real" && f.dataQuality && (
          <p className="mt-3 rounded-2xl border border-[#ffb020]/60 bg-[#ffb020]/10 p-3 text-sm">
            {fmt(e.dataWarning, { corr: num(f.dataQuality.correlation, 4), same: pct(f.dataQuality.identicalShare) })}
          </p>
        )}
      </Card>
      <Card className="grid content-start gap-5">
        <div>
          <h3 className="display text-xl font-semibold">{e.bandTitle}</h3>
          <p className="mt-1 mb-2 text-sm text-[var(--ink-2)]">{fmt(e.band, { w: num(f.conformal.halfWidthVeh, 1), got: pct(f.conformal.empirical, 1), t: pct(f.conformal.target) })}</p>
          <Meter value={f.conformal.empirical} target={f.conformal.target} label={e.bandTitle} />
          <div className="mt-2"><SourceBadge kind="SIM" t={t.badge} /></div>
        </div>
        {f.phaseChange && (
          <div>
            <h3 className="display text-xl font-semibold">{e.phaseTitle}</h3>
            <p className="mt-1 mb-2 text-sm text-[var(--ink-2)]">{fmt(e.phase, { s: num(f.phaseChange.halfWidthS), got: pct(f.phaseChange.empirical, 1), mae: num(f.phaseChange.maeS, 1) })}</p>
            <Meter value={f.phaseChange.empirical} target={f.phaseChange.target} label={e.phaseTitle} />
          </div>
        )}
        {f.anomalies && (
          <div>
            <h3 className="display text-xl font-semibold">{e.anomTitle}</h3>
            <p className="mt-1 text-sm text-[var(--ink-2)]">{fmt(e.anomalies, { r: pct(f.anomalies.injected.recall), p: pct(f.anomalies.injected.alarmPrecision), n: f.anomalies.injected.n, a: f.anomalies.injected.alarms })}</p>
          </div>
        )}
      </Card>
    </div>
  );
}

function Vision({ t }: { t: Messages }) {
  const v = results.vision;
  const e = t.evidence.vision;
  if (!v) return <Pending t={t} />;
  const names = e.modelNames as Record<string, string>;
  const cls = [...v.classes].filter((c) => c.ap50_95 !== null && c.n >= 20).sort((a, b) => (b.ap50_95 ?? 0) - (a.ap50_95 ?? 0));
  const demo = v.videos?.find((x) => x.junctionId.startsWith("DEMO"));
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="display text-2xl font-semibold">{e.title}</h3>
          <SourceBadge kind="MODEL" t={t.badge} />
        </div>
        <p className="mt-1 mb-4 text-sm text-[var(--ink-2)]">{fmt(e.test, { n: num(v.images), boxes: num(v.boxes), ms: num(v.speedMs?.uvh ?? 0) })}</p>
        <Bars format={(x) => num(x, 2)} max={1}
          rows={v.models.map((m): Bar => ({ key: m.id, label: names[m.id] ?? m.label, value: m.map50_95, strong: m.id === "uvh-common", muted: m.id === "coco-common", note: `mAP50 ${num(m.map50, 2)}` }))} />
        <p className="mt-3 text-xs text-[var(--ink-2)]">{e.map}</p>
        <p className="mt-4 rounded-2xl border border-[var(--line)] p-3 text-sm">{e.privacy}</p>
        {demo && <p className="mt-3 text-xs text-[var(--ink-2)]">{fmt(e.demo, { p: demo.pedestrianCrossings, s: demo.seconds })}</p>}
      </Card>
      <Card>
        <h3 className="display text-2xl font-semibold">{e.perClass}</h3>
        <p className="mt-1 mb-4 text-sm text-[var(--ink-2)]">{e.perClassNote}</p>
        <Bars format={(x) => num(x, 2)} max={1} rows={cls.map((c): Bar => ({ key: c.name, label: (e.classes as Record<string, string>)[c.name] ?? c.name, value: c.ap50_95 ?? 0, note: fmt(e.boxes, { n: num(c.n) }) }))} />
      </Card>
    </div>
  );
}
