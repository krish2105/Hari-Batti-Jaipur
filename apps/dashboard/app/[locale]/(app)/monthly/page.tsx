"use client";
// Monthly report for the DCP, printable in English or Hindi (switch language in the top bar, then
// Print → Save as PDF). Contents: corridor summary, per-junction metrics, top fixes from the
// fairness audit, citizen-report counts and the sources. Savings stay "not measured" until a new
// plan is applied and an after-period is measured: we never estimate savings we did not see.
import { useState } from "react";
import { Badge, Card, ErrorNote, Kpi, Loading, PageHead, SourceBadges } from "@/components/ui";
import { logExport, useApi } from "@/lib/api";
import { extraGreen } from "@/lib/fairness";
import { ALL_JUNCTIONS, healthColour } from "@/lib/health";
import { fmt, num, useT } from "@/lib/i18n";
import type { Fairness, Summary, SurveyDay } from "@/lib/types";

type Monthly = {
  month: string; surveyDates: string[]; junctions: Record<string, Summary | null>; survey: Record<string, SurveyDay[]>;
  citizenReports: Record<string, number>; savings: null | Record<string, number>; note: string; sources: Record<string, string>;
};

export default function MonthlyReport() {
  const { t, locale } = useT();
  const [month] = useState("2026-05");
  const res = useApi<Monthly>(`/reports/monthly?month=${month}`);
  const fair = useApi<Fairness>("/audit/fairness?date=2026-05-11&limit=5");
  const d = res.data;
  const days = d ? Object.values(d.survey).flat().filter((s) => d.surveyDates.includes(s.surveyDate)) : [];
  const vehicles = days.reduce((a, s) => a + s.totalVeh, 0);
  const present = ALL_JUNCTIONS.filter((j) => d?.junctions[j]?.health !== undefined && d?.junctions[j]?.health !== null);
  const flow = present.reduce((a, j) => a + (d!.junctions[j]!.flowPcu || 0), 0) || 1;
  const avgHealth = present.length ? present.reduce((a, j) => a + d!.junctions[j]!.health! * (d!.junctions[j]!.flowPcu || 0), 0) / flow : null;
  const generated = new Date().toLocaleDateString(locale === "hi" ? "hi-IN" : "en-IN", { dateStyle: "long" });

  const print = () => {
    logExport("print_report", { report: "monthly", month, locale });
    window.print();
  };

  return (
    <>
      <PageHead title={t.monthly.title} lead={t.monthly.lead}>
        <span className="panel-2 num px-3 py-2 text-xs">{t.monthly.month}: {month}</span>
        <button type="button" className="btn btn-primary" onClick={print} disabled={!d}>{t.common.print}</button>
      </PageHead>
      <ErrorNote error={res.error} />
      {!d ? <Loading /> : (
        <article className="flex flex-col gap-4">
          <div className="print-only">
            <p className="text-xl font-semibold">HariBatti · {t.monthly.title} · {month}</p>
            <p className="text-sm">{t.app.tagline}</p>
          </div>

          <Card title={t.monthly.summary} badge={<SourceBadges source={d.sources.metrics} />}>
            <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
              <Kpi label={t.monthly.vehicles} value={num(vehicles)} hint={fmt(t.monthly.days, { n: d.surveyDates.length })} badge={<Badge kind="SURVEY" />} />
              <Kpi label={t.overview.kpiHealth} value={num(avgHealth, 1)} unit="/ 100" tone={healthColour(avgHealth)} badge={<Badge kind="ASSUMED" />} />
              <Kpi label={t.monthly.reports} value={num(Object.values(d.citizenReports).reduce((a, n) => a + n, 0))} hint={Object.entries(d.citizenReports).map(([s, n]) => `${(t.reports as Record<string, string>)[s] ?? s} ${n}`).join(" · ")} badge={<Badge kind="CROWD" />} />
              <Kpi label={t.monthly.savings} value="—" hint={t.monthly.noSavings} />
            </div>
          </Card>

          <Card title={t.monthly.perJunction} badge={<span className="flex gap-1"><Badge kind="SURVEY" /><Badge kind="ASSUMED" /></span>}>
            <div className="overflow-x-auto">
              <table className="data min-w-[720px]">
                <thead><tr><th>{t.common.junction}</th><th>{t.monthly.vehicles}</th><th>{t.metric.health}</th><th>{t.metric.redWait}</th><th>{t.metric.starvation}</th><th>{t.metric.ped}</th><th>{t.junction.worstHour}</th></tr></thead>
                <tbody>
                  {ALL_JUNCTIONS.map((j) => {
                    const s = d.junctions[j];
                    const veh = (d.survey[j] ?? []).filter((x) => d.surveyDates.includes(x.surveyDate)).reduce((a, x) => a + x.totalVeh, 0);
                    return (
                      <tr key={j}>
                        <td className="num font-semibold">{j}</td>
                        <td className="num">{num(veh)}</td>
                        <td className="num font-semibold" style={{ color: healthColour(s?.health) }}>{num(s?.health, 1)}</td>
                        <td className="num">{num(s?.redWaitS)} s</td>
                        <td className="num">{num(s?.starvation, 2)}</td>
                        <td className="num">{num(s?.pedRatio, 2)}</td>
                        <td className="num">{s ? `${String(s.worstHour).padStart(2, "0")}:00` : "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          <Card insight="monthly.fixes" title={t.monthly.fixes} badge={<SourceBadges source={fair.data?.source} />}>
            {!fair.data ? <Loading /> : (
              <ol className="flex list-decimal flex-col gap-1.5 pl-5 text-sm">
                {fair.data.top.map((r) => {
                  const s = extraGreen(r.greenS, r.starvation);
                  return (
                    <li key={`${r.junctionId}-${r.approach}`}>
                      <span className="num font-semibold">{r.junctionId}</span> {r.approach}, {r.hourStart}: {t.metric.starvation} {num(r.starvation, 2)}
                      {s ? ` — ${fmt(t.audit.fixMore, { approach: r.approach, s, hour: r.hourStart })}` : ""}
                    </li>
                  );
                })}
              </ol>
            )}
          </Card>

          <Card title={t.monthly.sources}>
            <ul className="flex flex-col gap-1 text-sm">
              {Object.entries(d.sources).map(([k, v]) => <li key={k}><span className="faint">{k}:</span> {v}</li>)}
            </ul>
            <p className="muted mt-3 text-sm">{d.note}</p>
            <p className="faint mt-3 text-xs">{fmt(t.monthly.prepared, { date: generated })}</p>
            <p className="faint mt-1 text-xs">{t.app.readOnly}</p>
          </Card>
        </article>
      )}
    </>
  );
}
