"use client";
// Special modes — Event plans (stadium match, Teej, Gangaur, VIP) and the ambulance green-corridor
// planner: pick the junctions on the route in order and see roughly when each would need a green
// hold (POST /events/green-corridor). Recommendations for the control room only; never applied.
import { useState, type FormEvent } from "react";
import { Badge, Card, ErrorNote, Loading, PageHead } from "@/components/ui";
import { api, ApiError, useApi } from "@/lib/api";
import { ALL_JUNCTIONS } from "@/lib/health";
import { fmt, num, useT } from "@/lib/i18n";

type EventPlan = { id: string; name: string; nameHi: string; window: string; focus: string[]; advice: string; adviceHi?: string };
type Holds = { holds: { junctionId: string; arriveAfterS: number }[]; assumptions: { speedKmh: number; spacingM: number; spacingSource: string }; note: string };

export default function Events() {
  const { t, locale } = useT();
  const ev = useApi<{ events: EventPlan[]; note: string }>("/events");
  const [route, setRoute] = useState<string[]>(["J08", "J07", "J06", "J05"]);
  const [speed, setSpeed] = useState(40);
  const [spacing, setSpacing] = useState(500);
  const [plan, setPlan] = useState<Holds | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  const toggle = (id: string) => setRoute((r) => (r.includes(id) ? r.filter((x) => x !== id) : [...r, id]));
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      setPlan(await api<Holds>("/events/green-corridor", { method: "POST", json: { junctions: route, speed_kmh: speed, spacing_m: spacing } }));
    } catch (err) {
      setError(err as ApiError);
    }
  };
  const last = plan?.holds.at(-1)?.arriveAfterS ?? 0;

  return (
    <>
      <PageHead title={t.events.title} lead={t.events.lead} />
      <Card title={t.events.saved}>
        <ErrorNote error={ev.error} />
        {!ev.data ? <Loading /> : (
          <>
            <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
              {ev.data.events.map((e) => (
                <article key={e.id} className="panel-2 flex flex-col gap-2 p-4">
                  <h3 className="font-semibold">{locale === "hi" ? e.nameHi : e.name}</h3>
                  <p className="text-xs"><span className="faint">{t.events.window}:</span> <span className="num">{e.window}</span></p>
                  <p className="text-xs"><span className="faint">{t.events.focus}:</span> <span className="num font-semibold">{e.focus.join(", ")}</span></p>
                  <p className="muted text-sm">{locale === "hi" ? e.adviceHi ?? e.advice : e.advice}</p>
                </article>
              ))}
            </div>
            <p className="faint mt-3 text-xs">{ev.data.note}</p>
          </>
        )}
      </Card>

      <Card className="mt-4" insight="events.green-corridor" title={t.events.corridor} badge={<Badge kind="ASSUMED" />}>
        <p className="muted mb-4 max-w-3xl text-sm">{t.events.corridorLead}</p>
        <form onSubmit={submit} className="flex flex-col gap-4">
          <fieldset>
            <legend className="muted mb-2 text-sm">{t.events.route} ({t.events.routeHint})</legend>
            <div className="flex flex-wrap gap-2">
              {ALL_JUNCTIONS.map((id) => {
                const at = route.indexOf(id);
                return (
                  <button key={id} type="button" aria-pressed={at >= 0} onClick={() => toggle(id)}
                    className={`btn num !min-h-9 ${at >= 0 ? "!border-[var(--accent)] !bg-[var(--accent-soft)] !text-[var(--accent)]" : ""}`}>
                    {at >= 0 && <span className="rounded-full bg-[var(--accent)] px-1.5 text-[10px] text-[var(--bg)]">{at + 1}</span>}{id}
                  </button>
                );
              })}
            </div>
          </fieldset>
          <div className="flex flex-wrap items-end gap-3 text-sm">
            <label className="flex flex-col gap-1"><span className="muted">{t.events.speed}</span>
              <input className="field num w-28" type="number" min={10} max={60} value={speed} onChange={(e) => setSpeed(Number(e.target.value))} /></label>
            <label className="flex flex-col gap-1"><span className="muted">{t.events.spacing}</span>
              <input className="field num w-28" type="number" min={100} max={3000} step={50} value={spacing} onChange={(e) => setSpacing(Number(e.target.value))} /></label>
            <button type="submit" className="btn btn-primary" disabled={route.length === 0}>{t.events.plan}</button>
          </div>
        </form>
        <ErrorNote error={error} />
        {plan && (
          <div className="mt-5">
            {/* timeline: when the vehicle reaches each junction (SVG, so labels never clip or overlap) */}
            <svg viewBox="0 0 800 84" className="mb-4 w-full" role="img" aria-label={t.events.corridor}>
              <line x1="48" x2="752" y1="24" y2="24" stroke="var(--grid)" strokeWidth="6" strokeLinecap="round" />
              {plan.holds.map((h) => {
                const x = 48 + (last ? h.arriveAfterS / last : 0) * 704;
                return (
                  <g key={h.junctionId}>
                    <circle cx={x} cy={24} r={9} fill="#22c55e" stroke="var(--panel)" strokeWidth="3" />
                    <text x={x} y={54} textAnchor="middle" fontSize="14" fontWeight="700" fill="var(--ink)" className="num">{h.junctionId}</text>
                    <text x={x} y={74} textAnchor="middle" fontSize="12" fill="var(--ink-3)" className="num">+{num(h.arriveAfterS)} s</text>
                  </g>
                );
              })}
            </svg>
            <ol className="flex flex-col gap-1 text-sm">
              {plan.holds.map((h) => <li key={h.junctionId}>{fmt(t.events.holdAt, { j: h.junctionId, s: num(h.arriveAfterS) })}</li>)}
            </ol>
            <p className="faint mt-3 text-xs">{plan.note} {fmt(t.events.assumed, { speed: plan.assumptions.speedKmh, spacing: plan.assumptions.spacingM })}</p>
          </div>
        )}
      </Card>
    </>
  );
}
