"use client";
// My account (P8 W16): who you are signed in as, and your data rights under the DPDP Act 2023 —
// download everything stored under your email, ask for erasure, or end the session on the server.
import { useState } from "react";
import { Card, PageHead } from "@/components/ui";
import { api, ApiError, setSession } from "@/lib/api";
import { useSession } from "@/lib/session";
import { fmt, useT } from "@/lib/i18n";

export default function Account() {
  const { t } = useT();
  const a = t.account;
  const { session } = useSession();
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const exportData = async () => {
    try {
      const data = await api<unknown>("/privacy/me/export");
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `haribatti-my-data-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setMsg({ ok: false, text: e instanceof ApiError ? e.message : String(e) });
    }
  };
  const erase = async () => {
    if (!window.confirm(a.eraseConfirm)) return;
    try {
      const r = await api<{ id: number }>("/privacy/requests", { method: "POST", json: { kind: "erase" } });
      setMsg({ ok: true, text: fmt(a.requested, { id: r.id }) });
    } catch (e) {
      setMsg({ ok: false, text: e instanceof ApiError ? e.message : String(e) });
    }
  };
  const signOut = () => api("/auth/logout", { method: "POST" }).catch(() => undefined).finally(() => setSession(null));

  return (
    <>
      <PageHead title={a.title} lead={a.lead} />
      <div className="grid max-w-3xl gap-4">
        <Card>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="faint">{a.email}</dt><dd className="break-all font-semibold">{session?.email}</dd>
            <dt className="faint">{a.role}</dt><dd>{session ? (t.role as Record<string, string>)[session.role] ?? session.role : "—"}</dd>
          </dl>
        </Card>
        <Card title={a.export}><p className="muted mb-3 text-sm">{a.exportLead}</p><button type="button" className="btn btn-primary" onClick={exportData}>{a.export}</button></Card>
        <Card title={a.erase}><p className="muted mb-3 text-sm">{a.eraseLead}</p><button type="button" className="btn" onClick={erase}>{a.erase}</button></Card>
        <Card title={a.signOutAll}><p className="muted mb-3 text-sm">{a.signOutLead}</p><button type="button" className="btn" onClick={signOut}>{a.signOutAll}</button></Card>
        {msg && <p role="status" className={`text-sm ${msg.ok ? "text-[#16a34a]" : "text-[#ff3b30]"}`}>{msg.text}</p>}
        <p className="faint text-xs">{a.policy}</p>
      </div>
    </>
  );
}
