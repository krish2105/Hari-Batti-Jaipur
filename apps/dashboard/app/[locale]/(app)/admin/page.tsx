"use client";
// Admin only — the audit log: every sign-in, export, printed report, Plan Studio run and copilot
// question, newest first (GET /audit/log). Non-admins see a short note instead of the table.
import { useState } from "react";
import { Card, ErrorNote, Loading, PageHead, Segmented } from "@/components/ui";
import { roleAtLeast, useApi } from "@/lib/api";
import { useSession } from "@/lib/session";
import { useT } from "@/lib/i18n";
import type { AuditEvent } from "@/lib/types";

export default function AdminLog() {
  const { t, locale } = useT();
  const { session } = useSession();
  const isAdmin = roleAtLeast(session?.role, "Admin");
  const log = useApi<{ events: AuditEvent[] }>(isAdmin ? "/audit/log?limit=500" : null, { pollMs: 15000 });
  const [filter, setFilter] = useState("all");
  const events = (log.data?.events ?? []).filter((e) => filter === "all" || e.action === filter || (filter === "export" && e.action.startsWith("export")));

  if (!isAdmin) {
    return (
      <>
        <PageHead title={t.admin.title} />
        <Card><p className="text-sm">{t.admin.adminOnly}</p></Card>
      </>
    );
  }

  return (
    <>
      <PageHead title={t.admin.title} lead={t.admin.lead}>
        <Segmented label={t.admin.action} value={filter} onChange={setFilter} options={[
          { value: "all", label: t.admin.all }, { value: "login", label: t.admin.logins }, { value: "export", label: t.admin.exports },
          { value: "plan_run", label: t.nav.plans }, { value: "copilot_ask", label: t.nav.copilot },
        ]} />
      </PageHead>
      <ErrorNote error={log.error} />
      <Card>
        {!log.data ? <Loading /> : events.length === 0 ? <p className="muted text-sm">{t.common.empty}</p> : (
          <div className="overflow-x-auto">
            <table className="data min-w-[720px]">
              <thead><tr><th>{t.admin.when}</th><th>{t.admin.who}</th><th>{t.admin.action}</th><th>{t.admin.detail}</th></tr></thead>
              <tbody>
                {events.map((e) => (
                  <tr key={e.id}>
                    <td className="num whitespace-nowrap text-xs">{new Date(e.ts).toLocaleString(locale === "hi" ? "hi-IN" : "en-IN", { dateStyle: "medium", timeStyle: "medium" })}</td>
                    <td className="text-xs">{e.email ?? "—"}<span className="faint block">{e.role ? t.role[e.role as keyof typeof t.role] ?? e.role : ""}</span></td>
                    <td><span className="rounded-full bg-[var(--accent-soft)] px-2 py-0.5 text-xs font-semibold text-[var(--accent)]">{e.action}</span></td>
                    <td className="num max-w-[28rem] break-words text-[11px]">{e.detail && Object.keys(e.detail).length ? JSON.stringify(e.detail) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
