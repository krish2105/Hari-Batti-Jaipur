"use client";
// Screen 6 — AI Copilot. The officer asks in English or Hindi; the API asks local Ollama
// (qwen2.5:7b, no paid API) to write ONE read-only SQL query, runs it through the SQL guard, and
// answers only from the rows. We always show the answer, the SQL it ran, the rows and a chart.
// A 503 means Ollama is not running on this laptop: we say how to start it.
import { useState, type FormEvent } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Card, PageHead, SourceBadges } from "@/components/ui";
import { axis, grid, SERIES, tooltip } from "@/components/charts/theme";
import { api, ApiError } from "@/lib/api";
import { fmt, num, useT } from "@/lib/i18n";
import type { CopilotAnswer } from "@/lib/types";

type Turn = { q: string; a: CopilotAnswer | null; error: ApiError | null };

export default function Copilot() {
  const { t, locale } = useT();
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);

  const ask = async (question: string) => {
    if (question.trim().length < 3 || busy) return;
    setBusy(true);
    setQ("");
    setTurns((ts) => [{ q: question, a: null, error: null }, ...ts]);
    let turn: Turn;
    try {
      turn = { q: question, a: await api<CopilotAnswer>("/copilot/ask", { method: "POST", json: { question, lang: locale } }), error: null };
    } catch (e) {
      turn = { q: question, a: null, error: e as ApiError };
    }
    setTurns((ts) => [turn, ...ts.slice(1)]);
    setBusy(false);
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    ask(q);
  };

  return (
    <>
      <PageHead title={t.copilot.title} lead={t.copilot.lead}>
        <span className="panel-2 px-3 py-2 text-xs">{t.copilot.engine}: Ollama · qwen2.5:7b</span>
      </PageHead>

      <Card>
        <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row">
          <label className="sr-only" htmlFor="q">{t.copilot.placeholder}</label>
          <input id="q" className="field flex-1" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.copilot.placeholder} maxLength={500} autoComplete="off" />
          <button type="submit" className="btn btn-primary" disabled={busy || q.trim().length < 3}>{t.copilot.ask}</button>
        </form>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="faint">{t.copilot.examples}:</span>
          {[t.copilot.ex1, t.copilot.ex2, t.copilot.ex3].map((ex) => (
            <button key={ex} type="button" className="panel-2 px-2.5 py-1.5 text-left hover:border-[var(--accent)]" onClick={() => ask(ex)} disabled={busy}>{ex}</button>
          ))}
        </div>
      </Card>

      <div className="mt-4 flex flex-col gap-4" aria-live="polite">
        {turns.map((turn, i) => <Answer key={turns.length - i} turn={turn} />)}
      </div>
    </>
  );
}

function Answer({ turn }: { turn: Turn }) {
  const { t } = useT();
  const { a, error } = turn;
  return (
    <Card title={turn.q} badge={a ? <SourceBadges source={a.sourceLabel.includes("Survey") ? `SURVEY ${a.sourceLabel}` : a.sourceLabel} /> : undefined}>
      {!a && !error && <p role="status" className="flex items-center gap-2 text-sm"><span className="live-dot size-2 rounded-full bg-[var(--accent)]" /> {t.copilot.thinking}</p>}
      {error && (
        <p role="alert" className="rounded-lg border border-[#ff3b30]/40 bg-[#ff3b30]/10 p-3 text-sm">
          {error.status === 503 ? t.copilot.offline : error.status === 504 ? t.copilot.slow : error.status === 0 ? t.copilot.unreachable : fmt(t.common.error, { msg: error.message })}
        </p>
      )}
      {a && (
        <div className="flex flex-col gap-4">
          <p className="whitespace-pre-line leading-relaxed">{a.answer}</p>
          {a.error && <p className="text-sm text-[#ff3b30]">{a.error}</p>}
          {a.sql && (
            <details open className="panel-2 p-3">
              <summary className="cursor-pointer text-xs font-semibold">{t.copilot.sql}</summary>
              <pre className="num mt-2 overflow-x-auto whitespace-pre-wrap text-xs">{a.sql}</pre>
            </details>
          )}
          {a.rows.length > 0 && <AnswerChart a={a} />}
          {a.rows.length > 0 && (
            <details className="panel-2 p-3">
              <summary className="cursor-pointer text-xs font-semibold">{fmt(t.copilot.rows, { n: a.rows.length })}</summary>
              <div className="mt-2 max-h-80 overflow-auto">
                <table className="data">
                  <thead><tr>{a.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                  <tbody>{a.rows.slice(0, 200).map((r, i) => <tr key={i}>{r.map((v, j) => <td key={j} className="num">{typeof v === "number" ? num(v, 2) : String(v ?? "—")}</td>)}</tr>)}</tbody>
                </table>
              </div>
            </details>
          )}
          <p className="faint flex flex-wrap items-center gap-2 text-xs">{a.engine} · {a.model} <Badge kind="MODEL" /></p>
        </div>
      )}
    </Card>
  );
}

/** Draw the chart the model asked for, if its x / y columns exist; otherwise the first text + number columns. */
function AnswerChart({ a }: { a: CopilotAnswer }) {
  const { t } = useT();
  if (a.chart?.type === "table") return null;
  const numeric = a.columns.filter((_, i) => a.rows.some((r) => typeof r[i] === "number"));
  const y = a.chart?.y && a.columns.includes(a.chart.y) ? a.chart.y : numeric[0];
  const x = a.chart?.x && a.columns.includes(a.chart.x) ? a.chart.x : a.columns.find((c) => c !== y);
  if (!x || !y) return null;
  const xi = a.columns.indexOf(x);
  const yi = a.columns.indexOf(y);
  const data = a.rows.slice(0, 60).map((r) => ({ x: String(r[xi] ?? ""), y: Number(r[yi]) }));
  const Chart = a.chart?.type === "line" ? LineChart : BarChart;
  return (
    <figure>
      <figcaption className="faint mb-1 text-xs">{t.copilot.chart}: {y} × {x}</figcaption>
      <div className="h-[240px]">
        <ResponsiveContainer>
          <Chart data={data} margin={{ left: -6, right: 8, top: 8 }}>
            <CartesianGrid {...grid} />
            <XAxis dataKey="x" {...axis} />
            <YAxis {...axis} width={56} tickFormatter={(v: number) => num(v)} />
            <Tooltip {...tooltip} formatter={(v) => num(Number(v), 2)} />
            {a.chart?.type === "line" ? <Line dataKey="y" name={y} stroke={SERIES[0]} strokeWidth={2} dot={false} /> : <Bar dataKey="y" name={y} fill={SERIES[0]} />}
          </Chart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
