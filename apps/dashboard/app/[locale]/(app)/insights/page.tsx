"use client";
// Screen — ML & models. One card per analysis: digital-twin calibration (with every search trial),
// controller comparison, demand forecasting, anomaly detection and computer vision. Each result is
// read from GET /analytics/{name}; a Pending card is shown until its workstream has produced the file.
// Honest ML: every card shows the baseline, the held-out metric and the data size, plus its source.
import { Bar, BarChart, CartesianGrid, ErrorBar, Legend, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { Badge, Card, ErrorNote, Kpi, Loading, PageHead, Pending, SourceBadges } from "@/components/ui";
import { axis, grid, SERIES, tooltip } from "@/components/charts/theme";
import { useApi } from "@/lib/api";
import { fmt, num, useT } from "@/lib/i18n";
import type { Anomalies, CalibrationBest, Controllers, CvEval, Forecast, ForecastBlock, TableResult } from "@/lib/types";

const pct = (x: number | null | undefined, d = 0) => (x === null || x === undefined ? "—" : `${num(x * 100, d)}%`);

export default function Insights() {
  const { t } = useT();
  return (
    <>
      <PageHead title={t.insights.title} lead={t.insights.lead} />
      <div className="flex flex-col gap-4">
        <Calibration />
        <ControllersCard />
        <ForecastCard />
        <AnomaliesCard />
        <CvCard />
      </div>
    </>
  );
}

function Calibration() {
  const { t } = useT();
  const best = useApi<CalibrationBest>("/analytics/calibration");
  const trials = useApi<TableResult>("/analytics/calibration_trials");
  const b = best.data;
  const col = (name: string) => trials.data?.columns?.indexOf(name) ?? -1;
  const points = (trials.data?.rows ?? []).map((r) => ({
    trial: Number(r[col("trial")]),
    cal: Number(r[col("calibration_geh_share")]) * 100,
    val: Number(r[col("validation_geh_share")]) * 100,
    unserved: Number(r[col("unserved_share")]) * 100,
  })).filter((p) => Number.isFinite(p.cal));
  const pass = (x: number | null | undefined) => (x !== null && x !== undefined && x >= 0.85 ? t.insights.pass : t.insights.fail);

  return (
    <Card title={t.insights.calibration} badge={<span className="flex gap-1"><Badge kind="SIM" /><Badge kind="SURVEY" /></span>}>
      <p className="muted mb-3 max-w-3xl text-sm">{t.insights.calibrationLead}</p>
      <ErrorNote error={best.error} />
      {!b ? <Loading /> : !b.available ? <Pending what={t.insights.calibration} /> : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Kpi label={`${t.insights.cal} · ${t.insights.score}`} value={pct(b.calibration_geh_share)} hint={`${pass(b.calibration_geh_share)} · ${t.insights.target} 85%`} tone={(b.calibration_geh_share ?? 0) >= 0.85 ? "#22c55e" : "#ff3b30"} badge={<Badge kind="SIM" />} />
          <Kpi label={`${t.insights.val} · ${t.insights.score}`} value={pct(b.validation_geh_share)} hint={`${pass(b.validation_geh_share)} · ${t.insights.target} 85%`} tone={(b.validation_geh_share ?? 0) >= 0.85 ? "#22c55e" : "#ff3b30"} badge={<Badge kind="SIM" />} />
          <Kpi label={t.insights.unserved} value={pct(b.unserved_share)} hint={`${t.insights.target} < 5%`} tone={(b.unserved_share ?? 1) < 0.05 ? "#22c55e" : "#ff3b30"} badge={<Badge kind="SIM" />} />
          <Kpi label={t.insights.trials} value={num(b.trials)} hint={b.params ? Object.entries(b.params).map(([k, v]) => `${k}=${typeof v === "number" ? num(v, 2) : v}`).join(", ") : undefined} badge={<Badge kind="SIM" />} />
        </div>
      )}
      {points.length > 0 && (
        <>
          <h3 className="mt-5 mb-2 text-sm font-semibold">{t.insights.trialsChart}</h3>
          <div className="h-[260px]">
            <ResponsiveContainer>
              <ScatterChart margin={{ left: -6, right: 12, top: 8 }}>
                <CartesianGrid {...grid} vertical />
                <XAxis type="number" dataKey="cal" name={t.insights.cal} unit="%" {...axis} domain={[0, 100]} />
                <YAxis type="number" dataKey="val" name={t.insights.val} unit="%" {...axis} domain={[0, 100]} width={50} />
                <ZAxis type="number" dataKey="unserved" range={[40, 260]} name={t.insights.unserved} unit="%" />
                <Tooltip {...tooltip} formatter={(v) => `${num(Number(v), 1)}%`} />
                <Scatter name={t.insights.trial} data={points} fill={SERIES[0]} fillOpacity={0.75} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <p className="faint text-xs">{t.insights.trialsNote}</p>
        </>
      )}
    </Card>
  );
}

function ControllersCard() {
  const { t } = useT();
  const res = useApi<Controllers>("/analytics/controllers");
  const d = res.data;
  const rows = d?.controllers ?? [];
  const chart = rows.map((c) => ({ name: c.label, travel: c.travelTimeS.mean, travelCi: c.travelTimeS.ci95 ?? 0, wait: c.waitingTimeS.mean, waitCi: c.waitingTimeS.ci95 ?? 0 }));
  const cell = (m: { mean: number; ci95: number | null }, digits = 1) => `${num(m.mean, digits)}${m.ci95 !== null ? ` ± ${num(m.ci95, digits)}` : ""}`;
  return (
    <Card title={t.insights.controllers} badge={<Badge kind="SIM" />}>
      <p className="muted mb-3 max-w-3xl text-sm">{t.insights.controllersLead}</p>
      <ErrorNote error={res.error} />
      {!d ? <Loading /> : !d.available ? <Pending what={t.insights.controllers} /> : (
        <>
          <p className="faint mb-3 text-xs">{fmt(t.insights.controllersMeta, { train: d.trainDay ?? "—", evalDay: d.evalDay ?? "—", window: d.window ?? "—", seeds: d.seeds?.length ?? 0 })}</p>
          <div className="h-[280px]">
            <ResponsiveContainer>
              <BarChart data={chart} margin={{ left: -6, right: 8, top: 8 }}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="name" {...axis} interval={0} tick={{ fontSize: 10 }} />
                <YAxis {...axis} width={50} unit=" s" />
                <Tooltip {...tooltip} formatter={(v) => `${num(Number(v), 1)} s`} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar name={t.insights.travel} dataKey="travel" fill={SERIES[1]}><ErrorBar dataKey="travelCi" stroke="var(--ink-2)" width={4} /></Bar>
                <Bar name={t.insights.wait} dataKey="wait" fill={SERIES[0]}><ErrorBar dataKey="waitCi" stroke="var(--ink-2)" width={4} /></Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="data min-w-[760px]">
              <thead><tr><th>{t.insights.controller}</th><th>{t.insights.travel}</th><th>{t.insights.wait}</th><th>{t.plans.stops}</th><th>{t.insights.queue}</th><th>{t.insights.throughput}</th><th>CO₂ (kg)</th></tr></thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id}>
                    <td>{c.label}<span className="faint text-xs"> · {c.kind}</span></td>
                    <td className="num">{cell(c.travelTimeS)} s</td><td className="num">{cell(c.waitingTimeS)} s</td><td className="num">{cell(c.stops, 2)}</td>
                    <td className="num">{cell(c.queueVeh)}</td><td className="num">{cell(c.throughputVeh, 0)}</td><td className="num">{cell(c.co2Kg, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {d.note && <p className="faint mt-2 text-xs">{d.note}</p>}
        </>
      )}
    </Card>
  );
}

function ScoreTable({ block, title }: { block: ForecastBlock; title: string }) {
  const { t } = useT();
  const best = Math.min(...block.models.map((m) => m.wape));
  return (
    <div className="min-w-0">
      <h3 className="mb-1 flex flex-wrap items-center gap-2 text-sm font-semibold">{title} <SourceBadges source={block.data} /></h3>
      <p className="faint mb-2 text-xs">{fmt(t.insights.split, { train: block.train, test: block.test, nTrain: num(block.nTrain), nTest: num(block.nTest) })}</p>
      <div className="overflow-x-auto">
        <table className="data min-w-[420px]">
          <thead><tr><th>{t.insights.model}</th><th>MAE</th><th>RMSE</th><th>WAPE</th></tr></thead>
          <tbody>
            {block.models.map((m) => (
              <tr key={m.id}>
                <td>{m.label}{m.isBaseline && <span className="faint text-xs"> · {t.insights.baseline}</span>}</td>
                <td className="num">{num(m.mae, 1)}</td><td className="num">{num(m.rmse, 1)}</td>
                <td className="num font-semibold" style={{ color: m.wape === best ? "#22c55e" : undefined }}>{pct(m.wape, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ForecastCard() {
  const { t } = useT();
  const res = useApi<Forecast>("/analytics/forecast");
  const d = res.data;
  return (
    <Card title={t.insights.forecast} badge={<SourceBadges source={d?.source} />}>
      <p className="muted mb-3 max-w-3xl text-sm">{t.insights.forecastLead}</p>
      <ErrorNote error={res.error} />
      {!d ? <Loading /> : !d.available ? <Pending what={t.insights.forecast} /> : (
        <>
          <div className="grid gap-5 lg:grid-cols-2">
            {d.real && <ScoreTable block={d.real} title={t.insights.onSurvey} />}
            {d.sim && <ScoreTable block={d.sim} title={t.insights.onSim} />}
          </div>
          {d.conformal && (
            <p className="mt-4 text-sm">
              {fmt(t.insights.conformal, { target: pct(d.conformal.target), got: pct(d.conformal.empirical, 1), width: num(d.conformal.meanWidthPcu) })} <SourceBadges source={d.conformal.data} />
            </p>
          )}
          {d.note && <p className="faint mt-2 text-xs">{d.note}</p>}
        </>
      )}
    </Card>
  );
}

function AnomaliesCard() {
  const { t } = useT();
  const res = useApi<Anomalies>("/analytics/anomalies");
  const d = res.data;
  return (
    <Card title={t.insights.anomalies} badge={<SourceBadges source={d?.source} />}>
      <p className="muted mb-3 max-w-3xl text-sm">{t.insights.anomaliesLead}</p>
      <ErrorNote error={res.error} />
      {!d ? <Loading /> : !d.available ? <Pending what={t.insights.anomalies} /> : (
        <>
          {d.injected && <p className="mb-3 text-sm">{fmt(t.insights.injected, { p: pct(d.injected.precision), r: pct(d.injected.recall), n: num(d.injected.n) })} <SourceBadges source={d.injected.data} /></p>}
          <div className="overflow-x-auto">
            <table className="data min-w-[640px]">
              <thead><tr><th>{t.common.junction}</th><th>{t.common.date}</th><th>{t.common.hour}</th><th>{t.insights.kind}</th><th>{t.insights.anomalyScore}</th><th>{t.insights.why}</th></tr></thead>
              <tbody>
                {(d.items ?? []).slice(0, 15).map((a) => (
                  <tr key={`${a.junctionId}-${a.date}-${a.hour}-${a.kind}`}>
                    <td className="num font-semibold">{a.junctionId}</td><td className="num">{a.date}</td><td className="num">{String(a.hour).padStart(2, "0")}:00</td>
                    <td>{a.kind}</td><td className="num">{num(a.score, 2)}</td><td className="text-xs">{a.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="faint mt-2 text-xs">{d.method}{d.note ? ` · ${d.note}` : ""}</p>
        </>
      )}
    </Card>
  );
}

function CvCard() {
  const { t } = useT();
  const res = useApi<CvEval>("/analytics/cv");
  const d = res.data;
  return (
    <Card title={t.insights.cv} badge={d?.available ? <Badge kind="MODEL" /> : undefined}>
      <p className="muted mb-3 max-w-3xl text-sm">{t.insights.cvLead}</p>
      <ErrorNote error={res.error} />
      {!d ? <Loading /> : !d.available ? <Pending what={t.insights.cv} /> : (
        <>
          <p className="faint mb-2 text-xs">{fmt(t.insights.cvMeta, { dataset: d.dataset ?? "—", n: num(d.images), device: d.device ?? "—" })}</p>
          <div className="overflow-x-auto">
            <table className="data min-w-[520px]">
              <thead><tr><th>{t.insights.model}</th><th>mAP50:95</th><th>mAP50</th><th>{t.insights.licence}</th></tr></thead>
              <tbody>
                {(d.models ?? []).map((m) => (
                  <tr key={m.id}><td>{m.label}</td><td className="num font-semibold">{num(m.map50_95, 3)}</td><td className="num">{num(m.map50, 3)}</td><td className="text-xs">{m.licence}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          {d.classes && d.classes.length > 0 && (
            <div className="mt-4 h-[260px]">
              <ResponsiveContainer>
                <BarChart data={d.classes} layout="vertical" margin={{ left: 30, right: 12 }}>
                  <CartesianGrid {...grid} horizontal={false} vertical />
                  <XAxis type="number" {...axis} domain={[0, 1]} />
                  <YAxis type="category" dataKey="name" {...axis} width={110} tick={{ fontSize: 10 }} />
                  <Tooltip {...tooltip} formatter={(v) => num(Number(v), 3)} />
                  <Bar name="AP50:95" dataKey="ap50_95" fill={SERIES[5]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          {d.note && <p className="faint mt-2 text-xs">{d.note}</p>}
        </>
      )}
    </Card>
  );
}
