"use client";
// Admin only — Business (P8 W17): monthly usage per organisation (sites, members, active users,
// API calls) with a CSV for invoice support, and the pilot requests sent from the website form.
import { useState } from "react";
import { Card, ErrorNote, Loading, PageHead } from "@/components/ui";
import { api, API_URL, getSession, roleAtLeast, useApi } from "@/lib/api";
import { useSession } from "@/lib/session";
import { fmt, num, useT } from "@/lib/i18n";

type Usage = { month: string; tenants: { tenantId: string; tenant: string; kind: string; demo: boolean; sitesActive: number; members: number; activeUsers: number; apiCalls: number }[] };
type Lead = { id: number; name: string; organisation: string; role: string | null; email: string; phone: string | null; offer: string; city: string | null; message: string | null; status: string; createdAt: string };

export default function Business() {
  const { t, locale } = useT();
  const b = t.business;
  const { session } = useSession();
  const isAdmin = roleAtLeast(session?.role, "Admin");
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const usage = useApi<Usage>(isAdmin ? `/metering?month=${month}` : null, { pollMs: 60000 });
  const leads = useApi<{ leads: Lead[] }>(isAdmin ? "/leads" : null, { pollMs: 30000 });

  if (!isAdmin) return (<><PageHead title={b.title} /><Card><p className="text-sm">{b.adminOnly}</p></Card></>);

  const csv = async () => {
    const r = await fetch(`${API_URL}/metering.csv?month=${month}`, { headers: { authorization: `Bearer ${getSession()?.token ?? ""}` } });
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = `haribatti-usage-${month}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };
  const setStatus = async (id: number, status: string) => {
    await api(`/leads/${id}`, { method: "PATCH", json: { status } });
    leads.refresh();
  };

  return (
    <>
      <PageHead title={b.title} lead={b.lead}>
        <label className="flex items-center gap-2 text-xs"><span className="faint">{b.month}</span><input type="month" className="field num !min-h-9 !py-1" value={month} onChange={(e) => e.target.value && setMonth(e.target.value)} /></label>
        <button type="button" className="btn btn-primary" onClick={csv}>{b.csv}</button>
      </PageHead>
      <ErrorNote error={usage.error ?? leads.error} />
      <Card title={fmt(b.usage, { month })}>
        {!usage.data ? <Loading /> : (
          <div className="overflow-x-auto">
            <table className="data min-w-[640px]">
              <thead><tr><th>{b.tenant}</th><th>{b.sites}</th><th>{b.members}</th><th>{b.users}</th><th>{b.calls}</th></tr></thead>
              <tbody>
                {usage.data.tenants.map((r) => (
                  <tr key={r.tenantId}>
                    <td className="text-sm"><b>{r.tenant}</b>{r.demo && <span className="faint ml-1 text-xs">({b.demo})</span>}<span className="faint block text-xs">{r.kind}</span></td>
                    <td className="num">{num(r.sitesActive)}</td><td className="num">{num(r.members)}</td><td className="num">{num(r.activeUsers)}</td><td className="num font-semibold">{num(r.apiCalls)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="faint mt-3 text-xs">{b.note}</p>
      </Card>
      <Card className="mt-4" title={b.leads}>
        {!leads.data ? <Loading /> : leads.data.leads.length === 0 ? <p className="muted text-sm">{b.noLeads}</p> : (
          <div className="overflow-x-auto">
            <table className="data min-w-[760px]">
              <thead><tr><th>{b.received}</th><th>{b.org}</th><th>{b.contact}</th><th>{b.offer}</th><th>{b.status}</th></tr></thead>
              <tbody>
                {leads.data.leads.map((l) => (
                  <tr key={l.id}>
                    <td className="num whitespace-nowrap text-xs">{new Date(l.createdAt).toLocaleDateString(locale === "hi" ? "hi-IN" : "en-IN", { dateStyle: "medium" })}</td>
                    <td className="text-sm"><b>{l.organisation}</b><span className="faint block text-xs">{l.city ?? ""}</span>{l.message && <span className="block max-w-xs text-xs">{l.message}</span>}</td>
                    <td className="break-all text-xs">{l.name}{l.role ? ` · ${l.role}` : ""}<span className="block">{l.email}</span>{l.phone && <span className="block">{l.phone}</span>}</td>
                    <td className="text-xs">{l.offer}</td>
                    <td>
                      <select className="field !min-h-8 !py-1 text-xs" value={l.status} onChange={(e) => setStatus(l.id, e.target.value)} aria-label={b.status}>
                        {["new", "contacted", "closed"].map((s) => <option key={s} value={s}>{(b as Record<string, string>)[`s_${s}`]}</option>)}
                      </select>
                    </td>
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
