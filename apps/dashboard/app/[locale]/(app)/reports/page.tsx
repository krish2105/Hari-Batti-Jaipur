"use client";
// Screen 7 — Citizen reports from the app (broken, hidden or badly timed signals). Duplicates are
// grouped by junction + problem type. Operators can move a report New → Assigned → Fixed (PATCH);
// this only tracks follow-up work, it never touches a signal. No personal data is stored.
import Link from "next/link";
import { useState } from "react";
import { Badge, Card, ErrorNote, Kpi, Loading, PageHead } from "@/components/ui";
import { api, ApiError, roleAtLeast, useApi } from "@/lib/api";
import { useSession } from "@/lib/session";
import { fmt, num, useT } from "@/lib/i18n";
import type { CitizenReport } from "@/lib/types";

type List = { reports: CitizenReport[]; groups: { group_key: string; count: number }[] };
const STATUSES = ["New", "Assigned", "Fixed"] as const;
const TONE: Record<CitizenReport["status"], string> = { New: "#ff3b30", Assigned: "#ffb020", Fixed: "#22c55e" };

export default function Reports() {
  const { t, href, locale } = useT();
  const { session } = useSession();
  const canEdit = roleAtLeast(session?.role, "Operator");
  const list = useApi<List>("/reports");
  const [error, setError] = useState<ApiError | null>(null);
  const [saving, setSaving] = useState<number | null>(null);
  const reports = list.data?.reports ?? [];
  const typeLabel = (k: string) => (t.reports as Record<string, string>)[k] ?? k;
  const groupLabel = (key: string) => {
    const [j, type] = key.split(":");
    return `${j === "unmatched" ? t.reports.unmatched : j} · ${typeLabel(type ?? "")}`;
  };

  const setStatus = async (id: number, status: CitizenReport["status"]) => {
    setSaving(id);
    setError(null);
    try {
      await api(`/reports/${id}`, { method: "PATCH", json: { status } });
      await list.refresh();
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setSaving(null);
    }
  };

  const count = (s: CitizenReport["status"]) => reports.filter((r) => r.status === s).length;

  return (
    <>
      <PageHead title={t.reports.title} lead={t.reports.lead}><Badge kind="CROWD" /></PageHead>
      <ErrorNote error={list.error ?? error} />
      {!canEdit && <p className="mb-4 text-sm faint">{fmt(t.common.needsRole, { role: t.role[session?.role ?? "Viewer"], need: t.role.Operator })}</p>}

      <div className="grid grid-cols-3 gap-3">
        {STATUSES.map((s) => <Kpi key={s} label={t.reports[s]} value={num(count(s))} tone={TONE[s]} badge={<Badge kind="CROWD" />} />)}
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[320px_1fr]">
        <Card title={t.reports.groups} className="self-start">
          {!list.data ? <Loading /> : list.data.groups.length === 0 ? <p className="muted text-sm">{t.reports.none}</p> : (
            <ul className="flex flex-col gap-1.5 text-sm">
              {list.data.groups.map((g) => (
                <li key={g.group_key} className="panel-2 flex items-center justify-between gap-2 px-3 py-2">
                  <span className="min-w-0 truncate">{groupLabel(g.group_key)}</span>
                  <span className="num rounded-full bg-[var(--accent-soft)] px-2 text-xs font-semibold text-[var(--accent)]">{g.count}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title={t.reports.list}>
          {!list.data ? <Loading /> : reports.length === 0 ? <p className="muted text-sm">{t.reports.none}</p> : (
            <div className="overflow-x-auto">
              <table className="data min-w-[680px]">
                <thead><tr><th>#</th><th>{t.reports.type}</th><th>{t.common.junction}</th><th>{t.reports.note}</th><th>{t.reports.when}</th><th>{t.reports.status}</th></tr></thead>
                <tbody>
                  {reports.map((r) => (
                    <tr key={r.id}>
                      <td className="num faint">{r.id}</td>
                      <td>{typeLabel(r.type)}</td>
                      <td>{r.junction_id ? <Link className="num font-semibold hover:text-[var(--accent)]" href={href(`/junction/${r.junction_id}`)}>{r.junction_id}</Link> : <span className="faint text-xs">{t.reports.unmatched}</span>}
                        <span className="faint num block text-[11px]">{r.lat.toFixed(4)}, {r.lng.toFixed(4)}</span></td>
                      <td className="max-w-[18rem] text-xs">{r.note ?? <span className="faint">—</span>}</td>
                      <td className="num whitespace-nowrap text-xs">{new Date(r.created_at).toLocaleString(locale === "hi" ? "hi-IN" : "en-IN", { dateStyle: "medium", timeStyle: "short" })}</td>
                      <td>
                        {canEdit ? (
                          <select className="field !min-h-8 !py-1 text-xs" aria-label={`${t.reports.setStatus} #${r.id}`} value={r.status} disabled={saving === r.id}
                            onChange={(e) => setStatus(r.id, e.target.value as CitizenReport["status"])} style={{ color: TONE[r.status] }}>
                            {STATUSES.map((s) => <option key={s} value={s}>{t.reports[s]}</option>)}
                          </select>
                        ) : <span className="text-xs font-semibold" style={{ color: TONE[r.status] }}>{t.reports[r.status]}</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
