"use client";
// Pilot request form. Sends to the HariBatti API (POST /leads) when NEXT_PUBLIC_API_URL is set at
// build time; otherwise (the static site before the pilot server is public) it points to GitHub.
// Spam protection without third parties: a hidden honeypot field and the time the form was shown.
import { useEffect, useState, type FormEvent } from "react";
import type { Messages } from "@/lib/i18n";
import { fmt } from "@/lib/i18n";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
const REPO = "https://github.com/krish2105/Hari-Batti-Jaipur";
const OFFERS = ["pilot", "audit", "signal_command", "citizen_data", "fleet_api", "other"] as const;

export function ContactForm({ t }: { t: Messages["pages"] }) {
  const [startedAt, setStartedAt] = useState(0);
  const [state, setState] = useState<{ kind: "idle" | "sending" | "sent" | "error"; msg?: string }>({ kind: "idle" });
  useEffect(() => setStartedAt(Date.now()), []);

  if (!API) {
    return (
      <div className="surface max-w-2xl rounded-3xl p-6">
        <p className="text-[var(--ink-2)]">{t.f_offline}</p>
        <a className="mt-4 inline-block rounded-full bg-[var(--ink)] px-6 py-3 font-semibold text-[var(--bg)]" href={`${REPO}/issues/new?title=${encodeURIComponent(t.contactTitle)}`}>{t.f_github}</a>
      </div>
    );
  }

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body = Object.fromEntries(["name", "organisation", "role", "email", "phone", "city", "offer", "message", "website"].map((k) => [k, String(f.get(k) ?? "").trim()]));
    for (const k of ["role", "phone", "city", "message"]) if (!body[k]) delete body[k];
    setState({ kind: "sending" });
    try {
      const r = await fetch(`${API}/leads`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ ...body, consent: f.get("consent") === "on", startedAt }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : r.statusText);
      setState({ kind: "sent", msg: fmt(t.f_sent, { id: j.id }) });
    } catch (err) {
      setState({ kind: "error", msg: fmt(t.f_error, { msg: err instanceof Error ? err.message : String(err) }) });
    }
  };

  if (state.kind === "sent") return <p role="status" className="surface max-w-2xl rounded-3xl p-6 text-lg font-semibold text-[#15803d]">{state.msg}</p>;
  const field = "w-full rounded-xl border border-[var(--line)] bg-transparent px-3 py-2";
  return (
    <form onSubmit={submit} className="surface grid max-w-2xl gap-4 rounded-3xl p-6 sm:grid-cols-2">
      <label className="grid gap-1 text-sm">{t.f_name}<input name="name" required minLength={2} maxLength={100} className={field} autoComplete="name" /></label>
      <label className="grid gap-1 text-sm">{t.f_org}<input name="organisation" required minLength={2} maxLength={150} className={field} autoComplete="organization" /></label>
      <label className="grid gap-1 text-sm">{t.f_role}<input name="role" maxLength={100} className={field} /></label>
      <label className="grid gap-1 text-sm">{t.f_email}<input name="email" type="email" required maxLength={200} className={field} autoComplete="email" /></label>
      <label className="grid gap-1 text-sm">{t.f_phone}<input name="phone" type="tel" pattern="[0-9+ ()\-]{7,20}" className={field} autoComplete="tel" /></label>
      <label className="grid gap-1 text-sm">{t.f_city}<input name="city" maxLength={80} defaultValue="Jaipur" className={field} /></label>
      <label className="grid gap-1 text-sm sm:col-span-2">{t.f_offer}
        <select name="offer" className={field} defaultValue="pilot">{OFFERS.map((o) => <option key={o} value={o}>{t[`o_${o}`]}</option>)}</select>
      </label>
      <label className="grid gap-1 text-sm sm:col-span-2">{t.f_message}<textarea name="message" maxLength={2000} rows={4} className={field} /></label>
      {/* honeypot: hidden from people and screen readers; bots fill it */}
      <input name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" />
      <label className="flex items-start gap-2 text-sm sm:col-span-2"><input name="consent" type="checkbox" required className="mt-1" /> {t.f_consent}</label>
      <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
        <button disabled={state.kind === "sending"} className="rounded-full bg-[var(--ink)] px-6 py-3 font-semibold text-[var(--bg)] hover:opacity-90 disabled:opacity-60">{state.kind === "sending" ? t.f_sending : t.f_send}</button>
        {state.kind === "error" && <span role="alert" className="text-sm text-[#b91c1c]">{state.msg}</span>}
      </div>
    </form>
  );
}
