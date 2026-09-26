"use client";
// Admin only — onboarding wizard for a new organisation (P8 W13 tenant pack): organisation and
// branding (name only), sites (police: J01–J08 from the registry, never invented; others: their own
// gates), data sources (each value will carry this label), users, pilot + success measures, report
// template. One POST /tenants at the end. A timer shows how long onboarding took (goal: < 15 min).
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Card, ErrorNote, Loading, PageHead } from "@/components/ui";
import { api, ApiError, roleAtLeast, useApi } from "@/lib/api";
import { usePilot } from "@/lib/pilot";
import { useSession } from "@/lib/session";
import { fmt, useT } from "@/lib/i18n";
import type { JunctionInfo } from "@/lib/types";

type Kind = "police" | "campus" | "township" | "fleet" | "other";
const KINDS: Kind[] = ["police", "campus", "township", "fleet", "other"];
const SOURCES = ["SIM", "FIELD", "SURVEY", "CROWD", "ITMS"] as const;
const STEPS = ["s_org", "s_sites", "s_sources", "s_users", "s_pilot", "s_review"] as const;

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

export default function Onboarding() {
  const { t, href } = useT();
  const { session } = useSession();
  const isAdmin = roleAtLeast(session?.role, "Admin");
  const { tenants, refreshTenants, setTenantId } = usePilot();
  const registry = useApi<JunctionInfo[]>(isAdmin ? "/junctions" : null);
  const o = t.onboarding;

  const [step, setStep] = useState(0);
  const [started] = useState(() => Date.now());
  const [now, setNow] = useState(() => Date.now());
  const [name, setName] = useState("");
  const [kind, setKind] = useState<Kind>("campus");
  const [displayName, setDisplayName] = useState("");
  const [junctions, setJunctions] = useState<string[]>([]);
  const [gates, setGates] = useState([{ name: "", lat: "", lng: "" }]);
  const [sources, setSources] = useState<string[]>(["SIM"]);
  const [members, setMembers] = useState<{ email: string; role: "Viewer" | "Operator" | "Admin" }[]>([]);
  const [pilotName, setPilotName] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [kpis, setKpis] = useState<string[] | null>(null);
  const [title, setTitle] = useState("Pilot Evidence Pack");
  const [sections, setSections] = useState<string[]>(["kpis", "reviews", "feedback", "changes", "notes", "sources"]);
  const [footer, setFooter] = useState("Read-only analysis. No signal was controlled by HariBatti.");
  const [problem, setProblem] = useState<string | null>(null);
  const [apiErr, setApiErr] = useState<ApiError | null>(null);
  const [done, setDone] = useState<{ id: string; name: string; secs: number } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (done) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [done]);

  const templates = tenants?.kpiTemplates[kind] ?? [];
  const chosenKpis = kpis ?? templates.map((k) => k.key);
  const elapsed = Math.round((now - started) / 1000);
  const sites = useMemo(
    () => (kind === "police" ? junctions.map((id) => ({ id, name: id })) : gates.filter((g) => g.name.trim()).map((g) => ({ name: g.name.trim(), lat: g.lat ? Number(g.lat) : null, lng: g.lng ? Number(g.lng) : null }))),
    [kind, junctions, gates],
  );

  if (!isAdmin) {
    return (<><PageHead title={o.title} /><Card><p className="text-sm">{o.adminOnly}</p></Card></>);
  }

  /** Validation for the step being left; returns a message or null. */
  const check = (s: number): string | null => {
    if (s === 0 && name.trim().length < 2) return o.needName;
    if (s === 1 && sites.length === 0) return o.needSites;
    if (s === 4 && chosenKpis.length === 0) return o.needKpis;
    if (s === 4 && sections.length === 0) return o.needSections;
    if (s === 4 && !!start !== !!end) return o.datesBoth;
    return null;
  };
  const go = (to: number) => {
    const msg = to > step ? check(step) : null;
    setProblem(msg);
    if (!msg) setStep(to);
  };
  const toggle = (list: string[], v: string) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  const create = async () => {
    for (let s = 0; s < 5; s++) {
      const msg = check(s);
      if (msg) {
        setProblem(msg);
        setStep(s);
        return;
      }
    }
    setBusy(true);
    setApiErr(null);
    try {
      const r = await api<{ id: string; pilotId: number }>("/tenants", {
        method: "POST",
        json: {
          name: name.trim(), kind, displayName: displayName.trim() || null, sites, dataSources: sources,
          members: members.filter((m) => m.email.trim()), reportTemplate: { title, sections, footer },
          pilot: { name: pilotName.trim() || `${name.trim()} pilot`, start: start || null, end: end || null, kpis: chosenKpis },
        },
      });
      setDone({ id: r.id, name: name.trim(), secs: elapsed });
      refreshTenants();
    } catch (e) {
      setApiErr(e instanceof ApiError ? e : new ApiError(0, String(e)));
    } finally {
      setBusy(false);
    }
  };

  const kindLabel = (k: Kind) => o[`k_${k}` as const];
  const srcLabel = (s: string) => (s.startsWith("connector:") ? fmt(o.connector, { id: s.slice(10) }) : o[`src_${s}` as `src_${(typeof SOURCES)[number]}`]);

  if (done) {
    return (
      <>
        <PageHead title={o.title} />
        <Card>
          <p role="status" className="text-lg font-semibold text-[#16a34a]">{fmt(o.created, { name: done.name, t: mmss(done.secs) })}</p>
          <Link className="btn btn-primary mt-4" href={href("/pilot")} onClick={() => setTenantId(done.id)}>{o.openPilot}</Link>
        </Card>
      </>
    );
  }

  return (
    <>
      <PageHead title={o.title} lead={o.lead}>
        <span className="panel-2 num px-3 py-2 text-xs" aria-live="off">{fmt(o.elapsed, { t: mmss(elapsed) })}</span>
      </PageHead>
      <ol className="mb-4 flex flex-wrap gap-2 text-xs" aria-label={fmt(o.step, { n: step + 1, total: STEPS.length })}>
        {STEPS.map((s, i) => (
          <li key={s}>
            <button type="button" onClick={() => (i < step ? go(i) : undefined)} aria-current={i === step ? "step" : undefined}
              className={`rounded-full px-3 py-1 font-semibold ${i === step ? "bg-[var(--accent)] text-white" : i < step ? "bg-[var(--accent-soft)] text-[var(--accent)]" : "panel-2 faint"}`}>
              {i + 1}. {o[s]}
            </button>
          </li>
        ))}
      </ol>
      <Card title={`${fmt(o.step, { n: step + 1, total: STEPS.length })} · ${o[STEPS[step] ?? "s_org"]}`}>
        <div className="flex max-w-3xl flex-col gap-4 text-sm">
          {step === 0 && (
            <>
              <L label={o.orgName}><input className="field" autoFocus value={name} maxLength={80} onChange={(e) => setName(e.target.value)} /></L>
              <L label={o.kind}>
                <select className="field" value={kind} onChange={(e) => { setKind(e.target.value as Kind); setKpis(null); setSources(e.target.value === "police" ? ["SURVEY"] : ["SIM"]); }}>
                  {KINDS.map((k) => <option key={k} value={k}>{kindLabel(k)}</option>)}
                </select>
              </L>
              <L label={o.displayName}><input className="field" value={displayName} maxLength={120} placeholder={name} onChange={(e) => setDisplayName(e.target.value)} /></L>
              <p className="faint text-xs">{o.brandingNote}</p>
            </>
          )}

          {step === 1 && (kind === "police" ? (
            <>
              <p className="muted text-xs">{o.sitesPolice}</p>
              {!registry.data ? <Loading /> : (
                <div className="grid gap-2 sm:grid-cols-2">
                  {registry.data.map((j) => (
                    <label key={j.id} className="panel-2 flex items-center gap-2 px-3 py-2">
                      <input type="checkbox" checked={junctions.includes(j.id)} onChange={() => setJunctions(toggle(junctions, j.id))} />
                      <b className="num">{j.id}</b> {j.name}
                    </label>
                  ))}
                </div>
              )}
            </>
          ) : (
            <>
              <p className="muted text-xs">{o.sitesOther}</p>
              {gates.map((g, i) => (
                <div key={i} className="grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
                  <L label={`${o.siteName} ${i + 1}`}><input className="field w-full" value={g.name} maxLength={80} onChange={(e) => setGates(gates.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} /></L>
                  <L label={o.lat}><input className="field num w-full" inputMode="decimal" value={g.lat} onChange={(e) => setGates(gates.map((x, j) => (j === i ? { ...x, lat: e.target.value.replace(/[^0-9.\-]/g, "") } : x)))} /></L>
                  <L label={o.lng}><input className="field num w-full" inputMode="decimal" value={g.lng} onChange={(e) => setGates(gates.map((x, j) => (j === i ? { ...x, lng: e.target.value.replace(/[^0-9.\-]/g, "") } : x)))} /></L>
                  <button type="button" className="btn text-xs" disabled={gates.length === 1} onClick={() => setGates(gates.filter((_, j) => j !== i))}>{o.remove}</button>
                </div>
              ))}
              <button type="button" className="btn self-start text-xs" onClick={() => setGates([...gates, { name: "", lat: "", lng: "" }])}>+ {o.addSite}</button>
            </>
          ))}

          {step === 2 && (
            <>
              <p className="muted text-xs">{o.sourcesLead}</p>
              {[...SOURCES, ...(tenants?.connectors ?? []).map((c) => `connector:${c}`)].map((s) => (
                <label key={s} className="flex items-center gap-2"><input type="checkbox" checked={sources.includes(s)} onChange={() => setSources(toggle(sources, s))} /> {srcLabel(s)}</label>
              ))}
            </>
          )}

          {step === 3 && (
            <>
              <p className="muted text-xs">{o.usersLead}</p>
              {members.map((m, i) => (
                <div key={i} className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto_auto] items-end gap-2">
                  <L label={o.email}><input type="email" className="field w-full" value={m.email} onChange={(e) => setMembers(members.map((x, j) => (j === i ? { ...x, email: e.target.value } : x)))} /></L>
                  <L label={o.role}>
                    <select className="field" value={m.role} onChange={(e) => setMembers(members.map((x, j) => (j === i ? { ...x, role: e.target.value as typeof m.role } : x)))}>
                      {(["Viewer", "Operator", "Admin"] as const).map((r) => <option key={r} value={r}>{(t.role as Record<string, string>)[r] ?? r}</option>)}
                    </select>
                  </L>
                  <button type="button" className="btn text-xs" onClick={() => setMembers(members.filter((_, j) => j !== i))}>{o.remove}</button>
                </div>
              ))}
              <button type="button" className="btn self-start text-xs" onClick={() => setMembers([...members, { email: "", role: "Viewer" }])}>+ {o.addUser}</button>
            </>
          )}

          {step === 4 && (
            <>
              <L label={o.pilotName}><input className="field" value={pilotName} maxLength={120} placeholder={`${name} pilot`} onChange={(e) => setPilotName(e.target.value)} /></L>
              <div className="grid gap-2 sm:grid-cols-2">
                <L label={t.pilot.start}><input type="date" className="field num" value={start} onChange={(e) => setStart(e.target.value)} /></L>
                <L label={t.pilot.end}><input type="date" className="field num" value={end} onChange={(e) => setEnd(e.target.value)} /></L>
              </div>
              <fieldset className="min-w-0">
                <legend className="faint mb-1 text-xs">{o.kpis}</legend>
                <div className="flex flex-col gap-1">
                  {templates.map((k) => (
                    <label key={k.key} className="flex items-start gap-2"><input type="checkbox" className="mt-1" checked={chosenKpis.includes(k.key)} onChange={() => setKpis(toggle(chosenKpis, k.key))} /> <span>{k.label} <span className="faint text-xs">({k.unit})</span></span></label>
                  ))}
                </div>
              </fieldset>
              <L label={o.templateTitle}><input className="field" value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} /></L>
              <fieldset className="min-w-0">
                <legend className="faint mb-1 text-xs">{o.sections}</legend>
                <div className="flex flex-wrap gap-3">
                  {(tenants?.reportSections ?? []).map((s) => (
                    <label key={s} className="flex items-center gap-1.5"><input type="checkbox" checked={sections.includes(s)} onChange={() => setSections(toggle(sections, s))} /> {o[`sec_${s}` as `sec_kpis`]}</label>
                  ))}
                </div>
              </fieldset>
              <L label={o.footer}><input className="field" value={footer} maxLength={300} onChange={(e) => setFooter(e.target.value)} /></L>
            </>
          )}

          {step === 5 && (
            <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2">
              <dt className="faint">{o.orgName}</dt><dd><b>{name}</b> · {kindLabel(kind)}{displayName ? ` · “${displayName}”` : ""}</dd>
              <dt className="faint">{o.s_sites}</dt><dd>{sites.map((s) => ("id" in s ? s.id : s.name)).join(", ")}</dd>
              <dt className="faint">{o.s_sources}</dt><dd>{sources.join(", ") || "—"}</dd>
              <dt className="faint">{o.s_users}</dt><dd className="break-all">{members.filter((m) => m.email).map((m) => `${m.email} (${m.role})`).join(", ") || "—"}</dd>
              <dt className="faint">{o.pilotName}</dt><dd>{pilotName || `${name} pilot`} · {start ? `${start} → ${end}` : t.evidence.notSet}</dd>
              <dt className="faint">{o.kpis}</dt><dd>{chosenKpis.length}</dd>
              <dt className="faint">{o.templateTitle}</dt><dd>{title} · {sections.length} {o.sections.toLowerCase()}</dd>
            </dl>
          )}

          {problem && <p role="alert" className="text-xs text-[#ff3b30]">{problem}</p>}
          <ErrorNote error={apiErr} />
          <div className="flex flex-wrap gap-2">
            {step > 0 && <button type="button" className="btn" onClick={() => go(step - 1)}>{o.back}</button>}
            {step < STEPS.length - 1
              ? <button type="button" className="btn btn-primary" onClick={() => go(step + 1)}>{o.next}</button>
              : <button type="button" className="btn btn-primary" onClick={create} disabled={busy}>{o.create}</button>}
          </div>
        </div>
      </Card>
    </>
  );
}

function L({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex min-w-0 flex-col gap-1">
      <span className="faint text-xs">{label}</span>
      {children}
    </label>
  );
}
