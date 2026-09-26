"use client";
// Screen 4 — Fairness audit: every approach ranked by green starvation (green given ÷ green needed),
// with a suggested fix size and a pedestrian-time flag. "Print / save PDF" and "Download CSV" are
// both recorded in the audit log. The printed page is the one-click "Top fixes this month" sheet.
import Link from "next/link";
import { useState } from "react";
import { Badge, Card, ErrorNote, Loading, PageHead, Segmented, SourceBadges } from "@/components/ui";
import { downloadCsv, logExport, useApi } from "@/lib/api";
import { extraGreen } from "@/lib/fairness";
import { fmt, num, useT } from "@/lib/i18n";
import type { Fairness, FairnessRow } from "@/lib/types";

export default function Audit() {
  const { t, href, locale } = useT();
  const [date, setDate] = useState("2026-05-11");
  const [n, setN] = useState<"10" | "25">("10");
  const res = useApi<Fairness>(`/audit/fairness?date=${date}&limit=${n}`);
  const rows = res.data?.top ?? [];

  const fixes = (r: FairnessRow) => {
    const out: string[] = [];
    const s = extraGreen(r.greenS, r.starvation);
    if (s) out.push(fmt(t.audit.fixMore, { approach: r.approach, s, hour: r.hourStart }));
    if (r.pedRatio !== null && r.pedRatio < 1) out.push(t.audit.fixPed);
    return out;
  };

  const exportCsv = () => {
    logExport("export_csv", { screen: "audit", date, n: rows.length });
    downloadCsv(`haribatti-fairness-${date}.csv`, rows.map((r, i) => ({
      rank: i + 1, junction: r.junctionId, approach: r.approach, hour: r.hourStart, starvation: r.starvation.toFixed(3),
      red_wait_s: Math.round(r.redWaitS), ped_ratio: r.pedRatio?.toFixed(2) ?? "", vc: r.vc?.toFixed(2) ?? "", green_s: r.greenS ?? "",
      cycle_s: r.cycleS ?? "", suggested_extra_green_s: extraGreen(r.greenS, r.starvation) ?? "", source: res.data?.source ?? "",
    })));
  };
  const print = () => {
    logExport("export_pdf", { screen: "audit", date, n: rows.length, locale });
    window.print();
  };

  return (
    <>
      <PageHead title={t.audit.title} lead={t.audit.lead}>
        <Segmented label={t.common.date} value={date} onChange={setDate} options={[{ value: "2026-05-11", label: t.common.day11 }, { value: "2026-05-12", label: t.common.day12 }]} />
        <Segmented label={t.audit.top} value={n} onChange={setN} options={[{ value: "10", label: fmt(t.audit.top, { n: 10 }) }, { value: "25", label: fmt(t.audit.top, { n: 25 }) }]} />
        <button type="button" className="btn" onClick={exportCsv} disabled={!rows.length}>{t.common.csv}</button>
        <button type="button" className="btn btn-primary" onClick={print} disabled={!rows.length}>{t.common.print}</button>
      </PageHead>
      <ErrorNote error={res.error} />

      {/* printed header: title, date, sources (screen shows the page head instead) */}
      <div className="print-only mb-4">
        <p className="text-lg font-semibold">HariBatti · {t.audit.title} · {fmt(t.audit.top, { n: rows.length })}</p>
        <p className="text-sm">{date === "2026-05-11" ? t.common.day11 : t.common.day12} · {res.data?.source} · {res.data?.method}</p>
      </div>

      <Card insight="audit.top-fixes" title={fmt(t.audit.top, { n: rows.length || Number(n) })} badge={<SourceBadges source={res.data?.source} />}>
        {res.loading && !res.data ? <Loading /> : (
          <div className="overflow-x-auto">
            <table className="data min-w-[860px]">
              <thead>
                <tr>
                  <th>{t.audit.rank}</th><th>{t.common.junction}</th><th>{t.common.approach}</th><th>{t.common.hour}</th>
                  <th>{t.metric.starvation}</th><th>{t.metric.redWait}</th><th>{t.metric.ped}</th><th>{t.common.vc}</th><th>{t.audit.greenCycle}</th><th>{t.audit.fix}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={`${r.junctionId}-${r.approach}`}>
                    <td className="num faint">{i + 1}</td>
                    <td><Link className="num font-semibold hover:text-[var(--accent)]" href={href(`/junction/${r.junctionId}?date=${date}&hour=${r.hour}`)}>{r.junctionId}</Link></td>
                    <td>{r.approach}</td>
                    <td className="num">{r.hourStart}</td>
                    <td>
                      <span className="flex items-center gap-2">
                        <span className="num w-10" style={{ color: r.starvation < 0.8 ? "#ff3b30" : r.starvation < 1 ? "#ffb020" : undefined }}>{num(r.starvation, 2)}</span>
                        {/* bar: how far below "enough green" (1.0) this approach is */}
                        <span aria-hidden className="h-1.5 w-20 overflow-hidden rounded-full bg-[var(--grid)]">
                          <span className="block h-full rounded-full" style={{ width: `${Math.min(100, r.starvation * 100)}%`, background: r.starvation < 0.8 ? "#ff3b30" : r.starvation < 1 ? "#ffb020" : "#22c55e" }} />
                        </span>
                      </span>
                    </td>
                    <td className="num">{num(r.redWaitS)} s</td>
                    <td className="num" style={{ color: r.pedRatio !== null && r.pedRatio < 1 ? "#ffb020" : undefined }}>{num(r.pedRatio, 2)}</td>
                    <td className="num" style={{ color: (r.vc ?? 0) > 0.9 ? "#ff3b30" : undefined }}>{num(r.vc, 2)}</td>
                    <td className="num">{num(r.greenS)} / {num(r.cycleS)} s</td>
                    <td className="text-xs">{fixes(r).length ? fixes(r).map((f) => <p key={f}>{f}</p>) : <span className="faint">—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="faint mt-3 flex flex-wrap items-center gap-2 border-t border-[var(--line)] pt-3 text-xs">
          <span>{t.audit.method}: {res.data?.method}</span>
          <Badge kind="SURVEY" /><Badge kind="ASSUMED" />
        </div>
        <p className="faint mt-2 text-xs">{t.audit.fixNote}</p>
      </Card>
      <p className="print-only mt-6 text-xs">{t.app.readOnly}</p>
    </>
  );
}
