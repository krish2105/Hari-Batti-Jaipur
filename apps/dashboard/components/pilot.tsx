"use client";
// Pilot building blocks (P8 W13), shared by the Pilot page and the junction page:
// tenant picker, pilot dates, KPI tracker, officer notes + pins, weekly review, timing-change log
// and the useful/not-useful summary. Values without a measurement show "Not measured yet".
import { useState, type FormEvent, type ReactNode } from "react";
import { api, ApiError, roleAtLeast, useApi } from "@/lib/api";
import { improved, progressShare, usePilot } from "@/lib/pilot";
import { useSession } from "@/lib/session";
import { fmt, num, useT } from "@/lib/i18n";
import type { FeedbackSummary, Note, Pilot, PilotKpi, Review, Site, TimingChange } from "@/lib/types";
import { Badge, Card, ErrorNote, Loading, SourceBadges } from "./ui";

const SOURCES = ["FIELD", "SURVEY", "ITMS", "CROWD", "SIM"] as const;

function useRole() {
  const { session } = useSession();
  return { canWrite: roleAtLeast(session?.role, "Operator"), isAdmin: roleAtLeast(session?.role, "Admin") };
}

/** "Saved" / "Not saved: …" line under a form. */
function Status({ s }: { s: { ok: boolean; msg: string } | null }) {
  if (!s) return null;
  return <span role="status" className={`text-xs ${s.ok ? "text-[#16a34a]" : "text-[#ff3b30]"}`}>{s.msg}</span>;
}

function useSubmit() {
  const { t } = useT();
  const [status, setStatus] = useState<{ ok: boolean; msg: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const run = async (fn: () => Promise<unknown>, ok?: string) => {
    setBusy(true);
    setStatus(null);
    try {
      await fn();
      setStatus({ ok: true, msg: ok ?? t.pilot.saved });
      return true;
    } catch (e) {
      setStatus({ ok: false, msg: fmt(t.pilot.failed, { msg: e instanceof ApiError ? e.message : String(e) }) });
      return false;
    } finally {
      setBusy(false);
    }
  };
  return { status, busy, run };
}

function Field({ label, children, className = "" }: { label: string; children: ReactNode; className?: string }) {
  return (
    <label className={`flex min-w-0 flex-col gap-1 ${className}`}>
      <span className="faint text-xs">{label}</span>
      {children}
    </label>
  );
}

// ---- tenant picker ------------------------------------------------------------------------------

export function TenantPicker() {
  const { t } = useT();
  const { tenants, tenant, setTenantId } = usePilot();
  if (!tenants || tenants.tenants.length < 2) return tenant ? <span className="panel-2 px-3 py-2 text-xs font-semibold">{tenant.displayName ?? tenant.name}</span> : null;
  return (
    <label className="flex items-center gap-2 text-xs">
      <span className="faint">{t.pilot.tenant}</span>
      <select className="field !min-h-9 !py-1 text-sm" value={tenant?.id ?? ""} onChange={(e) => setTenantId(e.target.value)}>
        {tenants.tenants.map((x) => <option key={x.id} value={x.id}>{x.name}{x.demo ? " (SIM)" : ""}</option>)}
      </select>
    </label>
  );
}

// ---- pilot dates and progress -------------------------------------------------------------------

export function PilotDates({ pilot, onSaved }: { pilot: Pilot; onSaved: () => void }) {
  const { t, locale } = useT();
  const { isAdmin } = useRole();
  const [start, setStart] = useState(pilot.startDate ?? "");
  const [end, setEnd] = useState(pilot.endDate ?? "");
  const { status, busy, run } = useSubmit();
  const p = pilot.progress;
  const date = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString(locale === "hi" ? "hi-IN" : "en-IN", { dateStyle: "medium" });
  const text =
    p.status === "not_started" ? t.pilot.notStarted
      : p.status === "scheduled" ? fmt(t.pilot.scheduled, { date: date(pilot.startDate!) })
        : p.status === "ended" ? fmt(t.pilot.ended, { days: p.days ?? 0 })
          : fmt(t.pilot.running, { day: p.day ?? 0, days: p.days ?? 0 });
  const save = (e: FormEvent) => {
    e.preventDefault();
    run(() => api(`/pilots/${pilot.id}`, { method: "PATCH", json: { start: start || null, end: end || null } })).then((ok) => ok && onSaved());
  };
  return (
    <Card title={pilot.name} badge={<span className="faint text-xs">{t.pilot.dates}</span>}>
      <p className="text-sm font-semibold">{text}</p>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-[var(--panel-2)]" role="progressbar" aria-label={text} aria-valuemin={0} aria-valuemax={p.days ?? 0} aria-valuenow={p.day ?? 0}>
        <div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${Math.round(progressShare(p.day, p.days) * 100)}%` }} />
      </div>
      {pilot.startDate && <p className="faint mt-2 text-xs num">{date(pilot.startDate)} → {pilot.endDate ? date(pilot.endDate) : "—"}</p>}
      {isAdmin && (
        <form onSubmit={save} className="no-print mt-3 flex flex-wrap items-end gap-2">
          <Field label={t.pilot.start}><input type="date" className="field num" value={start} onChange={(e) => setStart(e.target.value)} /></Field>
          <Field label={t.pilot.end}><input type="date" className="field num" value={end} onChange={(e) => setEnd(e.target.value)} /></Field>
          <button className="btn" disabled={busy}>{t.pilot.saveDates}</button>
          <Status s={status} />
        </form>
      )}
    </Card>
  );
}

// ---- KPI tracker --------------------------------------------------------------------------------

/** A KPI unit in the reader's language ("approach-peaks" -> "दिशा-पीक"). */
export function useUnit() {
  const { t } = useT();
  return (u: string) => (t.pilot.units as Record<string, string>)[u] ?? u;
}

/** Text that the API sends in both languages (method, goal, note). */
export function pick(locale: string, en: string | null | undefined, hi: string | null | undefined) {
  return locale === "hi" && hi ? hi : en ?? null;
}

export function KpiValue({ m, unit: rawUnit }: { m: PilotKpi["baseline"]; unit: string }) {
  const { t, locale } = useT();
  const unit = useUnit()(rawUnit);
  const note = pick(locale, m.note, m.noteHi);
  if (m.value === null) return <span className="faint text-xs italic">{t.pilot.notMeasured}</span>;
  return (
    <span className="flex flex-col gap-1">
      <span className="num text-lg font-semibold leading-none">{num(m.value, m.value % 1 ? 1 : 0)}<span className="faint ml-1 text-xs font-normal">{unit}</span></span>
      <span className="flex flex-wrap items-center gap-1">
        {m.source && <SourceBadges source={m.source} />}
        {m.auto && <span className="faint text-[10px]">{t.pilot.auto}</span>}
      </span>
      {note && <span className="faint text-[11px] leading-snug">{note}</span>}
    </span>
  );
}

export function KpiTracker({ pilot, onSaved }: { pilot: Pilot; onSaved: () => void }) {
  const { t, locale } = useT();
  const { canWrite } = useRole();
  const unit = useUnit();
  const [editing, setEditing] = useState<number | null>(null);
  return (
    <Card title={t.pilot.kpis} insight={`pilot.${pilot.id}.kpis`}>
      <p className="muted mb-3 text-xs">{t.pilot.kpiLead}</p>
      <ul className="flex flex-col gap-3">
        {pilot.kpis.map((k) => {
          const better = improved(k.better, k.baseline.value, k.current.value);
          return (
            <li key={k.id} className="panel-2 p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-semibold">{locale === "hi" && k.labelHi ? k.labelHi : k.label}</p>
                  <p className="faint text-xs">{t.pilot.method}: {pick(locale, k.method, k.methodHi)}</p>
                </div>
                {canWrite && editing !== k.id && <button type="button" className="btn no-print !px-2.5 text-xs" onClick={() => setEditing(k.id)}>{t.pilot.edit}</button>}
              </div>
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-4">
                <div><p className="eyebrow mb-1">{t.pilot.baseline}</p><KpiValue m={k.baseline} unit={k.unit} /></div>
                <div><p className="eyebrow mb-1">{t.pilot.current}</p><KpiValue m={k.current} unit={k.unit} /></div>
                <div>
                  <p className="eyebrow mb-1">{t.pilot.change}</p>
                  {k.change ? (
                    <span className={`num text-sm font-semibold ${better === null ? "" : better ? "text-[#16a34a]" : "text-[#ff3b30]"}`}>
                      {k.change.abs > 0 ? "+" : ""}{num(k.change.abs, 1)} {unit(k.unit)}{k.change.pct !== null ? ` (${k.change.pct > 0 ? "+" : ""}${num(k.change.pct, 1)}%)` : ""}
                      {better !== null && <span className="ml-1 text-xs font-normal">{better ? t.pilot.improved : t.pilot.worse}</span>}
                    </span>
                  ) : <span className="faint text-xs">—</span>}
                </div>
                <div><p className="eyebrow mb-1">{t.pilot.target}</p><span className="text-xs">{pick(locale, k.targetNote, k.targetHi) ?? "—"}</span></div>
              </div>
              {editing === k.id && <KpiForm pilotId={pilot.id} kpi={k} onDone={(saved) => { setEditing(null); if (saved) onSaved(); }} />}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

function KpiForm({ pilotId, kpi, onDone }: { pilotId: number; kpi: PilotKpi; onDone: (saved: boolean) => void }) {
  const { t } = useT();
  const unit = useUnit();
  const init = (m: PilotKpi["baseline"]) => ({ value: m.auto || m.value === null ? "" : String(m.value), source: m.auto ? "FIELD" : m.source ?? "FIELD", note: m.auto ? "" : m.note ?? "" });
  const [b, setB] = useState(init(kpi.baseline));
  const [c, setC] = useState(init(kpi.current));
  const { status, busy, run } = useSubmit();
  const part = (m: typeof b) => ({ value: m.value === "" ? null : Number(m.value), source: m.value === "" ? null : m.source, note: m.note });
  const save = (e: FormEvent) => {
    e.preventDefault();
    const json: Record<string, unknown> = { current: part(c) };
    if (!kpi.baseline.auto || b.value !== "") json.baseline = part(b); // keep the survey-computed baseline unless replaced
    run(() => api(`/pilots/${pilotId}/kpis/${kpi.id}`, { method: "PATCH", json })).then((ok) => ok && onDone(true));
  };
  const row = (label: string, m: typeof b, set: (x: typeof b) => void) => (
    <fieldset className="grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-[8rem_9rem_1fr]">
      <legend className="eyebrow mb-1">{label}</legend>
      <Field label={`${t.pilot.value} (${unit(kpi.unit)})`}><input className="field num" inputMode="decimal" value={m.value} onChange={(e) => set({ ...m, value: e.target.value.replace(/[^0-9.\-]/g, "") })} /></Field>
      <Field label={t.pilot.source}>
        <select className="field" value={m.source} onChange={(e) => set({ ...m, source: e.target.value })}>
          {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </Field>
      <Field label={t.pilot.note}><input className="field" value={m.note} maxLength={300} onChange={(e) => set({ ...m, note: e.target.value })} /></Field>
    </fieldset>
  );
  return (
    <form onSubmit={save} className="no-print mt-3 flex flex-col gap-3 border-t border-[var(--line)] pt-3">
      {row(t.pilot.baseline, b, setB)}
      {row(t.pilot.current, c, setC)}
      <div className="flex flex-wrap items-center gap-2">
        <button className="btn btn-primary" disabled={busy}>{t.pilot.save}</button>
        <button type="button" className="btn" onClick={() => onDone(false)}>{t.pilot.cancel}</button>
        <Status s={status} />
      </div>
    </form>
  );
}

// ---- officer notes and pins ---------------------------------------------------------------------

export function NotesPanel({ tenantId, sites, siteId, approaches }: { tenantId: string; sites: Site[]; siteId?: string; approaches?: string[] }) {
  const { t, locale } = useT();
  const { canWrite } = useRole();
  const res = useApi<{ notes: Note[] }>(`/tenants/${tenantId}/notes${siteId ? `?site=${siteId}` : ""}`);
  const [site, setSite] = useState(siteId ?? sites[0]?.id ?? "");
  const [approach, setApproach] = useState("");
  const [text, setText] = useState("");
  const [pinned, setPinned] = useState(false);
  const { status, busy, run } = useSubmit();
  const siteName = (id: string) => sites.find((s) => s.id === id)?.name ?? id;

  const add = (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    run(() => api(`/tenants/${tenantId}/notes`, { method: "POST", json: { siteId: site, approach: approach || null, text, pinned } })).then((ok) => {
      if (ok) {
        setText("");
        setPinned(false);
        res.refresh();
      }
    });
  };
  const patch = (id: number, json: Record<string, boolean>) => api(`/tenants/${tenantId}/notes/${id}`, { method: "PATCH", json }).then(res.refresh);

  return (
    <Card title={t.pilot.notes} badge={<Badge kind="FIELD" />}>
      <p className="muted mb-3 text-xs">{t.pilot.notesLead}</p>
      {canWrite && (
        <form onSubmit={add} className="no-print mb-4 flex flex-col gap-2">
          <div className="grid gap-2 sm:grid-cols-2">
            {!siteId && (
              <Field label={t.pilot.site}>
                <select className="field" value={site} onChange={(e) => setSite(e.target.value)}>
                  {sites.map((s) => <option key={s.id} value={s.id}>{s.id} · {s.name}</option>)}
                </select>
              </Field>
            )}
            {approaches && approaches.length > 0 && (
              <Field label={t.pilot.approach}>
                <select className="field" value={approach} onChange={(e) => setApproach(e.target.value)}>
                  <option value="">{t.pilot.none}</option>
                  {approaches.map((a) => <option key={a} value={a}>{a}</option>)}
                </select>
              </Field>
            )}
          </div>
          <textarea className="field min-h-16" aria-label={t.pilot.addNote} placeholder={t.pilot.notePlaceholder} maxLength={1000} value={text} onChange={(e) => setText(e.target.value)} />
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-1.5 text-xs"><input type="checkbox" checked={pinned} onChange={(e) => setPinned(e.target.checked)} /> 📌 {t.pilot.pin}</label>
            <button className="btn btn-primary" disabled={busy || !text.trim()}>{t.pilot.addNote}</button>
            <Status s={status} />
          </div>
        </form>
      )}
      <ErrorNote error={res.error} />
      {!res.data ? <Loading /> : res.data.notes.length === 0 ? <p className="muted text-sm">{t.pilot.empty}</p> : (
        <ul className="flex flex-col gap-2">
          {res.data.notes.map((n) => (
            <li key={n.id} className={`panel-2 p-3 text-sm ${n.resolved ? "opacity-60" : ""}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs">
                  {n.pinned && <span aria-label={t.pilot.pinned}>📌 </span>}
                  <b className="num">{n.siteId}</b> {!siteId && siteName(n.siteId)}{n.approach ? ` · ${n.approach}` : ""}
                  {n.resolved && <span className="ml-2 rounded-full bg-[#16a34a]/15 px-2 text-[#16a34a]">{t.pilot.resolved}</span>}
                </span>
                {canWrite && (
                  <span className="no-print flex gap-1">
                    <button type="button" className="btn !min-h-7 !px-2 !py-0 text-[11px]" onClick={() => patch(n.id, { pinned: !n.pinned })}>{n.pinned ? t.pilot.unpin : t.pilot.pin}</button>
                    <button type="button" className="btn !min-h-7 !px-2 !py-0 text-[11px]" onClick={() => patch(n.id, { resolved: !n.resolved })}>{n.resolved ? t.pilot.reopen : t.pilot.resolve}</button>
                  </span>
                )}
              </div>
              <p className="mt-1 whitespace-pre-wrap">{n.text}</p>
              <p className="faint mt-1 text-[11px]">{n.author} · {new Date(n.createdAt).toLocaleString(locale === "hi" ? "hi-IN" : "en-IN", { dateStyle: "medium", timeStyle: "short" })}</p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

// ---- weekly review ------------------------------------------------------------------------------

const SCREENS = ["overview", "live", "audit", "plans", "insights", "copilot", "reports", "events", "monthly", "pilot"] as const;

function mondayOf(d: Date): string {
  const x = new Date(d);
  x.setDate(x.getDate() - ((x.getDay() + 6) % 7));
  return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}-${String(x.getDate()).padStart(2, "0")}`;
}

export function WeeklyReview({ pilotId }: { pilotId: number }) {
  const { t } = useT();
  const { canWrite } = useRole();
  const res = useApi<{ reviews: Review[] }>(`/pilots/${pilotId}/reviews`);
  const [week, setWeek] = useState(mondayOf(new Date()));
  const [a, setA] = useState({ daysUsed: 3, mostUseful: "audit", actionTaken: false, actionNote: "", missing: "", rating: 3 });
  const { status, busy, run } = useSubmit();
  const nav = t.nav as Record<string, string>;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    run(() => api<{ weekStart: string }>(`/pilots/${pilotId}/reviews`, { method: "POST", json: { weekStart: week, answers: a } }), fmt(t.pilot.reviewSaved, { date: mondayOf(new Date(`${week}T00:00:00`)) })).then((ok) => {
      if (ok) res.refresh();
    });
  };
  const reviews = res.data?.reviews ?? [];
  const avg = reviews.length ? reviews.reduce((s, r) => s + r.answers.rating, 0) / reviews.length : null;
  return (
    <Card title={t.pilot.weekly} badge={<Badge kind="FIELD" />}>
      <p className="muted mb-3 text-xs">{t.pilot.weeklyLead}</p>
      {canWrite ? (
        <form onSubmit={submit} className="no-print flex flex-col gap-3 text-sm">
          <Field label={t.pilot.weekOf}><input type="date" className="field num w-44" value={week} onChange={(e) => setWeek(e.target.value)} required /></Field>
          <Field label={`1. ${t.pilot.q1}`}>
            <input type="number" min={0} max={7} className="field num w-24" value={a.daysUsed} onChange={(e) => setA({ ...a, daysUsed: Math.max(0, Math.min(7, Number(e.target.value))) })} />
          </Field>
          <Field label={`2. ${t.pilot.q2}`}>
            <select className="field" value={a.mostUseful} onChange={(e) => setA({ ...a, mostUseful: e.target.value })}>
              {SCREENS.map((s) => <option key={s} value={s}>{nav[s] ?? s}</option>)}
            </select>
          </Field>
          <fieldset className="flex min-w-0 flex-col gap-1">
            <legend className="faint mb-1 text-xs">3. {t.pilot.q3}</legend>
            <div className="flex gap-4">
              <label className="flex items-center gap-1.5"><input type="radio" name="q3" checked={a.actionTaken} onChange={() => setA({ ...a, actionTaken: true })} /> {t.pilot.yes}</label>
              <label className="flex items-center gap-1.5"><input type="radio" name="q3" checked={!a.actionTaken} onChange={() => setA({ ...a, actionTaken: false })} /> {t.pilot.no}</label>
            </div>
            {a.actionTaken && <input className="field mt-1" aria-label={t.pilot.q3note} placeholder={t.pilot.q3note} maxLength={500} value={a.actionNote} onChange={(e) => setA({ ...a, actionNote: e.target.value })} />}
          </fieldset>
          <Field label={`4. ${t.pilot.q4}`}><textarea className="field min-h-14" maxLength={1000} value={a.missing} onChange={(e) => setA({ ...a, missing: e.target.value })} /></Field>
          <fieldset className="flex min-w-0 flex-col gap-1">
            <legend className="faint mb-1 text-xs">5. {t.pilot.q5}</legend>
            <div className="flex flex-wrap gap-2">
              {[1, 2, 3, 4, 5].map((n) => (
                <label key={n} className={`btn !min-h-8 !px-3 !py-0 ${a.rating === n ? "btn-primary" : ""}`}>
                  <input type="radio" name="q5" className="sr-only" checked={a.rating === n} onChange={() => setA({ ...a, rating: n })} />
                  {n}
                </label>
              ))}
            </div>
          </fieldset>
          <div className="flex flex-wrap items-center gap-2"><button className="btn btn-primary" disabled={busy}>{t.pilot.submitReview}</button><Status s={status} /></div>
        </form>
      ) : <p className="muted text-sm">{t.pilot.operatorOnly}</p>}
      <div className="mt-4 border-t border-[var(--line)] pt-3 text-sm">
        <p className="font-semibold">{t.pilot.reviews}: <span className="num">{reviews.length}</span>{avg !== null && <span className="faint font-normal"> · {t.pilot.avgRating} <b className="num">{num(avg, 1)}</b> / 5</span>}</p>
        <ul className="mt-2 flex flex-col gap-1 text-xs">
          {reviews.slice(0, 6).map((r) => (
            <li key={`${r.weekStart}-${r.email}`} className="faint"><span className="num">{r.weekStart}</span> · {r.email} · {r.answers.rating}/5 · {r.answers.daysUsed}d{r.answers.missing ? ` · “${r.answers.missing.slice(0, 80)}”` : ""}</li>
          ))}
        </ul>
      </div>
    </Card>
  );
}

// ---- timing-change log --------------------------------------------------------------------------

export function ChangeLog({ tenantId, sites }: { tenantId: string; sites: Site[] }) {
  const { t } = useT();
  const { canWrite } = useRole();
  const res = useApi<{ changes: TimingChange[] }>(`/tenants/${tenantId}/timing-changes`);
  const blank = { siteId: sites[0]?.id ?? "", changedOn: new Date().toISOString().slice(0, 10), timeWindow: "", before: "", after: "", reason: "" };
  const [f, setF] = useState(blank);
  const { status, busy, run } = useSubmit();
  const submit = (e: FormEvent) => {
    e.preventDefault();
    run(() => api(`/tenants/${tenantId}/timing-changes`, { method: "POST", json: { ...f, timeWindow: f.timeWindow || null, reason: f.reason || null } })).then((ok) => {
      if (ok) {
        setF({ ...blank, siteId: f.siteId });
        res.refresh();
      }
    });
  };
  return (
    <Card title={t.pilot.changes} badge={<Badge kind="FIELD" />}>
      <p className="muted mb-3 text-xs">{t.pilot.changesLead}</p>
      {canWrite && (
        <form onSubmit={submit} className="no-print mb-4 grid gap-2 sm:grid-cols-2">
          <Field label={t.pilot.site}>
            <select className="field" value={f.siteId} onChange={(e) => setF({ ...f, siteId: e.target.value })}>
              {sites.map((s) => <option key={s.id} value={s.id}>{s.id} · {s.name}</option>)}
            </select>
          </Field>
          <Field label={t.pilot.changedOn}><input type="date" className="field num" required value={f.changedOn} onChange={(e) => setF({ ...f, changedOn: e.target.value })} /></Field>
          <Field label={t.pilot.window}><input className="field num" placeholder="17:00–20:00" maxLength={40} value={f.timeWindow} onChange={(e) => setF({ ...f, timeWindow: e.target.value })} /></Field>
          <Field label={t.pilot.reason}><input className="field" maxLength={500} value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} /></Field>
          <Field label={t.pilot.before}><input className="field" required maxLength={300} placeholder="Main 45 s / cross 45 s" value={f.before} onChange={(e) => setF({ ...f, before: e.target.value })} /></Field>
          <Field label={t.pilot.after}><input className="field" required maxLength={300} placeholder="Main 60 s / cross 30 s" value={f.after} onChange={(e) => setF({ ...f, after: e.target.value })} /></Field>
          <div className="flex flex-wrap items-center gap-2 sm:col-span-2"><button className="btn btn-primary" disabled={busy}>{t.pilot.addChange}</button><Status s={status} /></div>
        </form>
      )}
      {!res.data ? <Loading /> : res.data.changes.length === 0 ? <p className="muted text-sm">{t.pilot.empty}</p> : (
        <div className="overflow-x-auto">
          <table className="data min-w-[640px]">
            <thead><tr><th>{t.pilot.changedOn}</th><th>{t.pilot.site}</th><th>{t.pilot.window}</th><th>{t.pilot.before}</th><th>{t.pilot.after}</th><th>{t.pilot.reason}</th></tr></thead>
            <tbody>
              {res.data.changes.map((c) => (
                <tr key={c.id}><td className="num text-xs">{c.changedOn}</td><td className="num font-semibold">{c.siteId}</td><td className="num text-xs">{c.timeWindow ?? "—"}</td><td className="text-xs">{c.before}</td><td className="text-xs">{c.after}</td><td className="text-xs">{c.reason ?? "—"}<span className="faint block">{c.enteredBy}</span></td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

// ---- feedback summary ---------------------------------------------------------------------------

export function FeedbackPanel({ tenantId }: { tenantId: string }) {
  const { t } = useT();
  const res = useApi<FeedbackSummary>(`/tenants/${tenantId}/feedback`, { pollMs: 15000 });
  const items = res.data?.items ?? [];
  return (
    <Card title={t.pilot.feedback}>
      <p className="muted mb-3 text-xs">{t.pilot.feedbackLead}</p>
      {!res.data ? <Loading /> : items.length === 0 ? <p className="muted text-sm">{t.pilot.empty}</p> : (
        <ul className="flex flex-col gap-2 text-sm">
          {items.map((i) => {
            const total = i.useful + i.notUseful;
            return (
              <li key={i.insight}>
                <div className="flex flex-wrap justify-between gap-2 text-xs"><span className="num">{i.insight}</span><span className="num">👍 {i.useful} · 👎 {i.notUseful}</span></div>
                <div className="mt-1 flex h-2 overflow-hidden rounded-full bg-[var(--panel-2)]" aria-hidden>
                  <div className="bg-[#16a34a]" style={{ width: `${(100 * i.useful) / total}%` }} />
                  <div className="bg-[#ff3b30]" style={{ width: `${(100 * i.notUseful) / total}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
