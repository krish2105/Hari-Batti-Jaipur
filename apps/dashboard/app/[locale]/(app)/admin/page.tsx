"use client";
// Admin only — the audit log: every sign-in, export, printed report, Plan Studio run and copilot
// question, newest first (GET /audit/log). Non-admins see a short note instead of the table.
import { useState } from "react";
import { Card, ErrorNote, Loading, PageHead, Segmented } from "@/components/ui";
import { api, roleAtLeast, useApi } from "@/lib/api";
import { useSession } from "@/lib/session";
import { fmt, useT } from "@/lib/i18n";
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
      <PrivacyRequests />
    </>
  );
}

type PrivacyRequest = { id: number; email: string; kind: string; note: string | null; status: string; created_at: string; handled_by: string | null };

/** Data-subject requests (P8 W16): Admins complete or reject them; completing an erasure anonymises the email. */
function PrivacyRequests() {
  const { t, locale } = useT();
  const a = t.account;
  const res = useApi<{ requests: PrivacyRequest[] }>("/privacy/requests");
  const [msg, setMsg] = useState<string | null>(null);
  const act = async (id: number, status: "done" | "rejected") => {
    const r = await api<{ rowsAnonymised: number }>(`/privacy/requests/${id}`, { method: "PATCH", json: { status } });
    setMsg(fmt(a.done, { n: r.rowsAnonymised }));
    res.refresh();
  };
  return (
    <Card className="mt-4" title={a.requests}>
      <p className="muted mb-3 text-xs">{a.requestsLead}</p>
      {msg && <p role="status" className="mb-2 text-xs text-[#16a34a]">{msg}</p>}
      {!res.data ? <Loading /> : res.data.requests.length === 0 ? <p className="muted text-sm">{a.none}</p> : (
        <div className="overflow-x-auto">
          <table className="data min-w-[640px]">
            <thead><tr><th>{a.when}</th><th>{a.email}</th><th>{a.kind}</th><th>{a.status}</th><th /></tr></thead>
            <tbody>
              {res.data.requests.map((r) => (
                <tr key={r.id}>
                  <td className="num text-xs">{new Date(r.created_at).toLocaleString(locale === "hi" ? "hi-IN" : "en-IN", { dateStyle: "medium", timeStyle: "short" })}</td>
                  <td className="break-all text-xs">{r.email}{r.note ? <span className="faint block">{r.note}</span> : null}</td>
                  <td className="text-xs">{r.kind}</td>
                  <td className="text-xs">{r.status}</td>
                  <td className="whitespace-nowrap">{r.status === "open" && (<><button type="button" className="btn !min-h-7 !px-2 !py-0 text-[11px]" onClick={() => act(r.id, "done")}>{a.complete}</button>{" "}<button type="button" className="btn !min-h-7 !px-2 !py-0 text-[11px]" onClick={() => act(r.id, "rejected")}>{a.reject}</button></>)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
