"use client";
// Screen 5 — Plan Studio. (1) Run a before/after simulation in the SUMO digital twin: POST
// /plans/simulate (Operator), then poll GET /plans/simulate/{id}. (2) A time-space diagram of the
// main road for any plan, with today's zero offsets, a green wave at the chosen speed, or the
// optimised offsets from the optimisation study (/analytics/timespace) once it exists.
// Everything here is simulation (SIM) on ASSUMED timing; nothing is ever sent to a signal.
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Badge, Card, ErrorNote, Loading, PageHead, Segmented } from "@/components/ui";
import { TimeSpace } from "@/components/TimeSpace";
import { api, ApiError, roleAtLeast, useApi } from "@/lib/api";
import { ALL_JUNCTIONS } from "@/lib/health";
import { useSession } from "@/lib/session";
import { waveOffsets, type TsJunction } from "@/lib/timespace";
import { fmt, num, useT } from "@/lib/i18n";
import type { PlanLibrary, SimRun, SimSide, TimespaceResult } from "@/lib/types";

type PlanId = "even" | "demand2" | "webster4";

export default function PlanStudio() {
  const { t } = useT();
  return (
    <>
      <PageHead title={t.plans.title} lead={t.plans.lead}>
        <Badge kind="SIM" /><Badge kind="ASSUMED" />
      </PageHead>
      <Simulator />
      <TimeSpaceCard />
    </>
  );
}

function Simulator() {
  const { t, fmtPlan } = usePlanLabels();
  const { session } = useSession();
  const canRun = roleAtLeast(session?.role, "Operator");
  const [baseline, setBaseline] = useState<PlanId>("even");
  const [proposed, setProposed] = useState<PlanId | "custom">("demand2");
  const [junction, setJunction] = useState("J05");
  const [custom, setCustom] = useState({ cycle_s: 90, main_green_s: 45, cross_green_s: 30 });
  const [start, setStart] = useState("18:15");
  const [minutes, setMinutes] = useState(15);
  const [run, setRun] = useState<SimRun | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  // poll the job every 3 s until it is done or failed
  useEffect(() => {
    if (!run || run.status === "done" || run.status === "failed") return;
    const id = setTimeout(async () => {
      try {
        setRun(await api<SimRun>(`/plans/simulate/${run.id}`));
      } catch (e) {
        setError(e as ApiError);
      }
    }, 3000);
    return () => clearTimeout(id);
  }, [run]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const body = proposed === "custom"
      ? { baseline, proposed: null, junction_id: junction, custom, start, minutes }
      : { baseline, proposed, start, minutes };
    try {
      const r = await api<{ id: string; status: SimRun["status"] }>("/plans/simulate", { method: "POST", json: body });
      setRun({ id: r.id, status: r.status, request: body, result: null, error: null });
    } catch (err) {
      setError(err as ApiError);
    }
  };

  const busy = run !== null && (run.status === "queued" || run.status === "running");
  const plans: PlanId[] = ["even", "demand2", "webster4"];

  return (
    <div className="grid gap-4 xl:grid-cols-[380px_1fr]">
      <Card title={t.plans.setup}>
        {!canRun && <p className="mb-3 rounded-lg border border-[var(--line)] bg-[var(--accent-soft)] p-3 text-sm">{fmt(t.common.needsRole, { role: t.role[session?.role ?? "Viewer"], need: t.role.Operator })}</p>}
        <form onSubmit={submit} className="flex flex-col gap-3 text-sm">
          <label className="flex flex-col gap-1">
            <span className="muted">{t.plans.baseline}</span>
            <select className="field" value={baseline} onChange={(e) => setBaseline(e.target.value as PlanId)}>
              {plans.map((p) => <option key={p} value={p}>{fmtPlan(p)}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="muted">{t.plans.proposed}</span>
            <select className="field" value={proposed} onChange={(e) => setProposed(e.target.value as PlanId | "custom")}>
              {plans.map((p) => <option key={p} value={p}>{fmtPlan(p)}</option>)}
              <option value="custom">{t.plans.planCustom}</option>
            </select>
          </label>
          {proposed === "custom" && (
            <fieldset className="panel-2 grid grid-cols-2 gap-2 p-3">
              <legend className="px-1 text-xs font-semibold">{t.plans.custom}</legend>
              <label className="col-span-2 flex flex-col gap-1">
                <span className="muted">{t.common.junction}</span>
                <select className="field" value={junction} onChange={(e) => setJunction(e.target.value)}>
                  {ALL_JUNCTIONS.map((j) => <option key={j}>{j}</option>)}
                </select>
              </label>
              <NumField label={t.plans.cycle} value={custom.cycle_s} min={40} max={240} onChange={(v) => setCustom({ ...custom, cycle_s: v })} />
              <NumField label={t.plans.main} value={custom.main_green_s} min={10} max={200} onChange={(v) => setCustom({ ...custom, main_green_s: v })} />
              <NumField label={t.plans.cross} value={custom.cross_green_s} min={10} max={200} onChange={(v) => setCustom({ ...custom, cross_green_s: v })} />
            </fieldset>
          )}
          <div className="grid grid-cols-2 gap-2">
            <label className="flex flex-col gap-1">
              <span className="muted">{t.plans.start}</span>
              <input className="field num" type="time" value={start} onChange={(e) => setStart(e.target.value)} required />
            </label>
            <NumField label={t.plans.minutes} value={minutes} min={5} max={60} onChange={setMinutes} />
          </div>
          <button type="submit" className="btn btn-primary" disabled={!canRun || busy}>{t.plans.run}</button>
          <p className="faint text-xs">{t.plans.readOnly}</p>
        </form>
      </Card>

      <Card insight="plans.result" title={t.plans.result} badge={run?.result ? <Badge kind="SIM" /> : undefined}>
        <ErrorNote error={error} />
        {!run && <p className="muted text-sm">{t.plans.idle}</p>}
        {busy && (
          <div role="status" className="flex items-center gap-3 text-sm">
            <span className="live-dot size-2.5 rounded-full bg-[var(--accent)]" /> {t.plans.running} <span className="faint num">({run?.id})</span>
          </div>
        )}
        {run?.status === "failed" && <p role="alert" className="rounded-lg border border-[#ff3b30]/40 bg-[#ff3b30]/10 p-3 text-sm">{fmt(t.plans.failed, { msg: (run.error ?? "").split("\n").slice(-3).join(" ") })}</p>}
        {run?.result && <Compare before={run.result.baseline} after={run.result.proposed} change={run.result.changePct} note={`${run.result.window} · ${run.result.geometryLabel} · ${run.result.note}`} />}
      </Card>
    </div>
  );
}

function NumField({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (v: number) => void }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="muted">{label}</span>
      <input className="field num" type="number" inputMode="numeric" value={value} min={min} max={max} onChange={(e) => onChange(Number(e.target.value))} required />
    </label>
  );
}

/** Before/after table; for delay, stops and CO2 a fall is good (green), for trips a rise is good. */
function Compare({ before, after, change, note }: { before: SimSide; after: SimSide; change: Record<string, number | null>; note: string }) {
  const { t } = useT();
  const rows: { key: keyof SimSide; label: string; unit: string; digits: number; lowerIsBetter: boolean }[] = [
    { key: "meanDelayS", label: t.plans.delay, unit: "s", digits: 1, lowerIsBetter: true },
    { key: "meanStops", label: t.plans.stops, unit: "", digits: 2, lowerIsBetter: true },
    { key: "co2PerTripG", label: t.plans.co2, unit: "g", digits: 0, lowerIsBetter: true },
    { key: "tripsCompleted", label: t.plans.trips, unit: "", digits: 0, lowerIsBetter: false },
    { key: "teleports", label: t.plans.teleports, unit: "", digits: 0, lowerIsBetter: true },
  ];
  return (
    <>
      <div className="overflow-x-auto">
        <table className="data min-w-[520px]">
          <thead>
            <tr><th /><th>{t.plans.before}<br /><span className="faint normal-case">{before.label}</span></th><th>{t.plans.after}<br /><span className="faint normal-case">{after.label}</span></th><th>{t.plans.change}</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const c = change[r.key as string];
              const good = c === null || c === undefined ? null : r.lowerIsBetter ? c < 0 : c > 0;
              return (
                <tr key={r.key}>
                  <td>{r.label}</td>
                  <td className="num">{num(before[r.key] as number, r.digits)} {r.unit}</td>
                  <td className="num">{num(after[r.key] as number, r.digits)} {r.unit}</td>
                  <td className="num font-semibold" style={{ color: good === null ? undefined : good ? "#22c55e" : "#ff3b30" }}>
                    {c === null || c === undefined ? "—" : `${c > 0 ? "+" : ""}${num(c, 1)}%`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="faint mt-3 text-xs">{note}</p>
    </>
  );
}

function usePlanLabels() {
  const { t } = useT();
  const fmtPlan = (p: string) => (p === "even" ? t.plans.planEven : p === "demand2" ? t.plans.planDemand2 : p === "webster4" ? t.plans.planWebster4 : p);
  return { t, fmtPlan };
}

function TimeSpaceCard() {
  const { t, fmtPlan } = usePlanLabels();
  const lib = useApi<PlanLibrary>("/plans/library");
  const opt = useApi<TimespaceResult>("/analytics/timespace");
  const [plan, setPlan] = useState<PlanId>("demand2");
  const [speed, setSpeed] = useState(35);
  const [offsets, setOffsets] = useState<"zero" | "wave" | "opt">("zero");
  const optimised = opt.data?.available ? opt.data : null;

  const js = useMemo<TsJunction[]>(() => {
    if (offsets === "opt" && optimised?.junctions) {
      return optimised.junctions.map((j) => ({ id: j.id, x: j.x, cycle: j.cycleS, green: j.greenS, offset: j.offsetS }));
    }
    const order = lib.data?.order ?? [];
    const per = lib.data?.plans?.[plan]?.junctions ?? {};
    const spacing = lib.data?.spacingM ?? 500;
    const base = order.flatMap((id, i) => {
      const p = per[id];
      return p ? [{ id, x: i * spacing, cycle: p.cycleS, green: p.mainGreenS ?? 0, offset: 0 }] : [];
    });
    if (offsets !== "wave") return base;
    const w = waveOffsets(base, speed / 3.6);
    return base.map((j, i) => ({ ...j, offset: w[i] ?? 0 }));
  }, [lib.data, plan, offsets, speed, optimised]);

  const offsetOptions: { value: "zero" | "wave" | "opt"; label: string }[] = [
    { value: "zero", label: t.plans.tsZero },
    { value: "wave", label: t.plans.tsWave },
    ...(optimised ? [{ value: "opt" as const, label: t.plans.tsOpt }] : []),
  ];

  return (
    <Card className="mt-4" insight="plans.time-space" title={t.plans.tsTitle} badge={<span className="flex gap-1"><Badge kind={offsets === "opt" ? "SIM" : "ASSUMED"} /></span>}>
      <p className="muted mb-3 max-w-3xl text-sm">{t.plans.tsLead}</p>
      {!lib.data && !lib.error ? <Loading /> : lib.data && !lib.data.available ? (
        <p className="muted text-sm">{t.plans.noLibrary}</p>
      ) : (
        <>
          <div className="mb-3 flex flex-wrap items-center gap-3 text-sm">
            {offsets !== "opt" && (
              <label className="flex items-center gap-2">
                <span className="muted">{t.plans.tsPlan}</span>
                <select className="field" value={plan} onChange={(e) => setPlan(e.target.value as PlanId)}>
                  {(["even", "demand2", "webster4"] as const).map((p) => <option key={p} value={p}>{fmtPlan(p)}</option>)}
                </select>
              </label>
            )}
            <label className="flex items-center gap-2">
              <span className="muted">{t.plans.tsSpeed}</span>
              <input type="range" min={20} max={50} step={5} value={speed} onChange={(e) => setSpeed(Number(e.target.value))} aria-valuetext={`${speed} km/h`} />
              <span className="num w-16">{speed} km/h</span>
            </label>
            <Segmented label={t.plans.tsOffsets} value={offsets} onChange={setOffsets} options={offsetOptions} />
          </div>
          <div className="overflow-x-auto">
            <TimeSpace js={js} speedMs={speed / 3.6} label={t.plans.tsTitle} />
          </div>
          <p className="faint mt-2 text-xs">
            {offsets === "opt" && optimised ? `${optimised.note ?? ""} ` : ""}
            {t.plans.tsNote}{!optimised ? ` ${t.plans.tsOptPending}` : ""}
          </p>
        </>
      )}
      <ErrorNote error={lib.error} />
    </Card>
  );
}
