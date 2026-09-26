"use client";
// Pilot Evidence Pack (P8 W13), printable in English or Hindi (switch language in the top bar, then
// Print → Save as PDF). Sections follow the tenant's report template. Measures nobody has measured
// yet are printed as clearly marked placeholders, never as estimates.
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { KpiValue, pick, useUnit } from "@/components/pilot";
import { Badge, Card, ErrorNote, Loading, PageHead } from "@/components/ui";
import { logExport, useApi } from "@/lib/api";
import { usePilot } from "@/lib/pilot";
import { fmt, num, useT } from "@/lib/i18n";
import type { Evidence } from "@/lib/types";

export default function EvidencePage() {
  return (
    <Suspense fallback={<Loading />}>
      <EvidencePack />
    </Suspense>
  );
}

function EvidencePack() {
  const { t, locale } = useT();
  const unit = useUnit();
  const params = useSearchParams();
  const { tenant } = usePilot();
  const pilotId = params.get("pilot") ?? (tenant?.pilots[0]?.id ? String(tenant.pilots[0].id) : null);
  const res = useApi<Evidence>(pilotId ? `/pilots/${pilotId}/evidence` : null);
  const e = res.data;
  const dateFmt = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString(locale === "hi" ? "hi-IN" : "en-IN", { dateStyle: "long" });
  const generated = new Date().toLocaleDateString(locale === "hi" ? "hi-IN" : "en-IN", { dateStyle: "long" });
  const show = (s: string) => !!e && e.tenant.reportTemplate.sections.includes(s);

  const print = () => {
    logExport("print_report", { report: "pilot_evidence", pilot: pilotId, locale });
    window.print();
  };

  return (
    <>
      <PageHead title={e?.tenant.reportTemplate.title ?? t.evidence.title} lead={t.evidence.lead}>
        <button type="button" className="btn btn-primary" onClick={print} disabled={!e}>{t.common.print}</button>
      </PageHead>
      <ErrorNote error={res.error} />
      {!e ? <Loading /> : (
        <article className="flex flex-col gap-4" data-testid="evidence-pack">
          <p className="print-only text-sm">HariBatti · {e.tenant.displayName ?? e.tenant.name}</p>

          <Card title={e.tenant.displayName ?? e.tenant.name} badge={e.tenant.demo ? <Badge kind="SIM" /> : undefined}>
            <p className="text-sm"><span className="faint">{t.evidence.period}:</span> <b className="num">{e.pilot.startDate ? `${dateFmt(e.pilot.startDate)} → ${e.pilot.endDate ? dateFmt(e.pilot.endDate) : "—"}` : t.evidence.notSet}</b></p>
            <p className="faint mt-1 text-xs">{e.pilot.name} · {fmt(t.evidence.generated, { date: generated })}</p>
            {e.placeholders.length > 0 && <p className="mt-3 rounded-lg border border-dashed border-[#ffb020] p-2 text-xs">{fmt(t.evidence.placeholders, { n: e.placeholders.length })}</p>}
          </Card>

          {show("kpis") && (
            <Card title={t.pilot.kpis}>
              <div className="overflow-x-auto">
                <table className="data min-w-[720px]">
                  <thead><tr><th>{t.pilot.kpis}</th><th>{t.pilot.baseline}</th><th>{t.pilot.current}</th><th>{t.pilot.change}</th><th>{t.pilot.target}</th></tr></thead>
                  <tbody>
                    {e.pilot.kpis.map((k) => (
                      <tr key={k.id}>
                        <td className="text-sm"><b>{locale === "hi" && k.labelHi ? k.labelHi : k.label}</b><span className="faint block text-[11px]">{pick(locale, k.method, k.methodHi)}</span></td>
                        <td>{k.baseline.value === null ? <Placeholder /> : <KpiValue m={k.baseline} unit={k.unit} />}</td>
                        <td>{k.current.value === null ? <Placeholder /> : <KpiValue m={k.current} unit={k.unit} />}</td>
                        <td className="num text-xs">{k.change ? `${k.change.abs > 0 ? "+" : ""}${num(k.change.abs, 1)} ${unit(k.unit)}${k.change.pct !== null ? ` (${num(k.change.pct, 1)}%)` : ""}` : "—"}</td>
                        <td className="text-xs">{pick(locale, k.targetNote, k.targetHi) ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {show("reviews") && (
            <Card title={t.evidence.reviewsTitle} badge={<Badge kind="FIELD" />}>
              {e.reviews.count === 0 ? <p className="muted text-sm">{t.evidence.noReviews}</p> : (
                <>
                  <p className="text-sm">{fmt(t.evidence.reviewsN, { n: e.reviews.count, r: num(e.reviews.avgRating, 1), d: num(e.reviews.avgDaysUsed, 1) })}</p>
                  {e.reviews.actions.length > 0 && (<><p className="mt-3 text-xs font-semibold">{t.evidence.actions}</p><ul className="list-disc pl-5 text-sm">{e.reviews.actions.map((a, i) => <li key={i}><span className="num faint">{a.weekStart}</span> {a.note || "—"}</li>)}</ul></>)}
                  {e.reviews.missing.length > 0 && (<><p className="mt-3 text-xs font-semibold">{t.evidence.missing}</p><ul className="list-disc pl-5 text-sm">{e.reviews.missing.map((a, i) => <li key={i}><span className="num faint">{a.weekStart}</span> {a.text}</li>)}</ul></>)}
                </>
              )}
            </Card>
          )}

          {show("feedback") && (
            <Card title={t.evidence.feedbackTitle}>
              {e.feedback.items.length === 0 ? <p className="muted text-sm">{t.pilot.empty}</p> : (
                <ul className="flex flex-col gap-1 text-sm">
                  <li className="font-semibold">{fmt(t.evidence.votes, { u: e.feedback.total.useful, n: e.feedback.total.notUseful })}</li>
                  {e.feedback.items.map((i) => <li key={i.insight} className="text-xs"><span className="num">{i.insight}</span> — {fmt(t.evidence.votes, { u: i.useful, n: i.notUseful })}</li>)}
                </ul>
              )}
            </Card>
          )}

          {show("changes") && (
            <Card title={t.evidence.changesTitle} badge={<Badge kind="FIELD" />}>
              {e.changes.length === 0 ? <p className="muted text-sm">{t.pilot.empty}</p> : (
                <ul className="flex flex-col gap-1 text-sm">
                  {e.changes.map((c) => <li key={c.id}><b className="num">{c.siteId}</b> <span className="num faint">{c.changedOn}{c.timeWindow ? ` · ${c.timeWindow}` : ""}</span> — {c.before} → {c.after}{c.reason ? ` (${c.reason})` : ""}</li>)}
                </ul>
              )}
            </Card>
          )}

          {show("notes") && (
            <Card title={t.evidence.notesTitle} badge={<Badge kind="FIELD" />}>
              {e.notes.length === 0 ? <p className="muted text-sm">{t.pilot.empty}</p> : (
                <ul className="flex flex-col gap-1 text-sm">
                  {e.notes.map((n) => <li key={n.id}>{n.pinned ? "📌 " : ""}<b className="num">{n.siteId}</b>{n.approach ? ` · ${n.approach}` : ""}: {n.text}{n.resolved ? ` (${t.pilot.resolved})` : ""}</li>)}
                </ul>
              )}
            </Card>
          )}

          {show("sources") && (
            <Card title={t.evidence.sourcesTitle}>
              <ul className="flex flex-col gap-1 text-sm">{Object.entries(e.sources).map(([k, v]) => <li key={k}><b>{k}</b>: {v}</li>)}</ul>
              <p className="muted mt-3 text-sm">{e.readOnly}</p>
            </Card>
          )}
          {e.tenant.reportTemplate.footer && <p className="faint text-xs">{e.tenant.reportTemplate.footer}</p>}
        </article>
      )}
    </>
  );
}

function Placeholder() {
  const { t } = useT();
  return <span className="inline-block rounded border border-dashed border-[#ffb020] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#b7791f]">{t.evidence.placeholderTag}</span>;
}
