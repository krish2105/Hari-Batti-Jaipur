"use client";
// System status (P8 W11): the four services now (polled every 5 s), open and recent alerts
// (feed stale / junction dark / impossible values), and the 30-day uptime ledger against the 99% goal.
import { Card, ErrorNote, Loading, PageHead } from "@/components/ui";
import { useApi } from "@/lib/api";
import { fmt, num, useT } from "@/lib/i18n";

type Status = { api: boolean; database: boolean; redis: boolean; signal_feed: boolean; feedSource: string; messagesReceived: number; openAlerts: string[] };
type Alert = { id: number; key: string; kind: string; source: string | null; junctionId: string | null; message: string; openedAt: string; closedAt: string | null };
type Uptime = { days: number; services: Record<string, { day: string; checks: number; uptimePct: number }[]>; overall: Record<string, number | null>; goalPct: number };

const SERVICES = ["api", "database", "redis", "signal_feed"] as const;
const pctColour = (p: number | null | undefined, goal: number) => (p == null ? "var(--ink-3)" : p >= goal ? "#16a34a" : p >= 95 ? "#ffb020" : "#ff3b30");

export default function StatusPage() {
  const { t, locale } = useT();
  const s = t.status;
  const status = useApi<Status>("/monitor/status", { pollMs: 5000 });
  const alerts = useApi<{ alerts: Alert[] }>("/monitor/alerts?limit=50", { pollMs: 10000 });
  const uptime = useApi<Uptime>("/monitor/uptime?days=30", { pollMs: 60000 });
  const when = (d: string) => new Date(d).toLocaleString(locale === "hi" ? "hi-IN" : "en-IN", { dateStyle: "medium", timeStyle: "short" });
  const kind = (k: string) => (s as Record<string, string>)[`kind_${k}`] ?? k;
  const open = (alerts.data?.alerts ?? []).filter((a) => !a.closedAt);

  return (
    <>
      <PageHead title={s.title} lead={s.lead} />
      <ErrorNote error={status.error} />
      <Card title={s.services} badge={status.data ? <span className="faint text-xs">{fmt(s.feedSource, { src: status.data.feedSource, n: num(status.data.messagesReceived) })}</span> : undefined}>
        {!status.data ? <Loading /> : (
          <ul className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {SERVICES.map((k) => {
              const up = status.data![k];
              return (
                <li key={k} className="panel-2 flex items-center gap-3 p-3" data-testid={`svc-${k}`}>
                  <span aria-hidden className={`inline-block size-3 rounded-full ${up ? "live-dot" : ""}`} style={{ background: up ? "#22c55e" : "#ff3b30" }} />
                  <span className="min-w-0"><span className="block text-sm font-semibold">{s[k]}</span><span className={`text-xs ${up ? "text-[#16a34a]" : "text-[#ff3b30]"}`}>{up ? s.up : s.down}</span></span>
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      <div className="mt-4 grid min-w-0 gap-4 xl:grid-cols-2">
        <Card title={s.openAlerts}>
          {!alerts.data ? <Loading /> : open.length === 0 ? <p className="text-sm text-[#16a34a]">{s.noOpen}</p> : (
            <ul className="flex flex-col gap-2 text-sm">
              {open.map((a) => <li key={a.id} className="rounded-lg border border-[#ff3b30]/40 bg-[#ff3b30]/10 p-2"><b>{kind(a.kind)}</b> — {a.message}<span className="faint block text-xs">{s.opened}: {when(a.openedAt)}</span></li>)}
            </ul>
          )}
        </Card>
        <Card title={s.recent}>
          {!alerts.data ? <Loading /> : alerts.data.alerts.length === 0 ? <p className="muted text-sm">{s.noAlerts}</p> : (
            <div className="max-h-72 overflow-auto">
              <table className="data min-w-[480px]">
                <thead><tr><th>{s.opened}</th><th>{t.common.source}</th><th /></tr></thead>
                <tbody>
                  {alerts.data.alerts.map((a) => (
                    <tr key={a.id}>
                      <td className="num whitespace-nowrap text-xs">{when(a.openedAt)}</td>
                      <td className="text-xs">{kind(a.kind)}{a.junctionId ? ` · ${a.junctionId}` : ""}{a.source ? ` · ${a.source}` : ""}</td>
                      <td className="text-xs">{a.message}<span className="faint block">{a.closedAt ? `${s.closed}: ${when(a.closedAt)}` : s.stillOpen}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <Card className="mt-4" title={s.uptime}>
        <p className="muted mb-3 text-xs">{s.uptimeLead}</p>
        {!uptime.data ? <Loading /> : SERVICES.every((k) => !(uptime.data!.services[k] ?? []).length) ? <p className="muted text-sm">{s.noChecks}</p> : (
          <ul className="flex flex-col gap-4">
            {SERVICES.map((k) => {
              const days = uptime.data!.services[k] ?? [];
              const overall = uptime.data!.overall[k];
              return (
                <li key={k}>
                  <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2 text-sm">
                    <span className="font-semibold">{s[k]}</span>
                    <span className="num text-xs"><b style={{ color: pctColour(overall, uptime.data!.goalPct) }}>{overall == null ? "—" : `${num(overall, 2)}%`}</b> <span className="faint">{s.overall} · {fmt(s.goal, { pct: uptime.data!.goalPct })}</span></span>
                  </div>
                  <div className="flex h-8 items-end gap-[3px]" role="img" aria-label={`${s[k]} ${overall ?? "—"}%`}>
                    {days.map((d) => (
                      <span key={d.day} title={`${d.day}: ${d.uptimePct}% (${d.checks})`} className="w-2 flex-1 rounded-sm" style={{ height: `${Math.max(8, d.uptimePct)}%`, background: pctColour(d.uptimePct, uptime.data!.goalPct) }} />
                    ))}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </>
  );
}
