"use client";
// Phase ring: one signal cycle drawn as a donut. Each coloured arc is a stage (the approaches that
// get green together); the thin amber arcs are the intergreen (amber + all-red) between stages.
// Stages are rebuilt from the metrics plan: approaches with the same road type and green share a stage.
import { SERIES } from "./charts/theme";
import { fmt, num, useT } from "@/lib/i18n";
import type { ApproachInfo } from "@/lib/types";

export type Stage = { names: string[]; greenS: number };

/** Group approaches into stages: main road first, then cross roads; equal green = same stage. */
export function stagesFrom(greens: Record<string, number>, approaches: ApproachInfo[]): Stage[] {
  const main = new Set(approaches.filter((a) => a.isMain).map((a) => a.name));
  const groups = new Map<string, Stage>();
  const ordered = Object.entries(greens).sort(([a], [b]) => Number(main.has(b)) - Number(main.has(a)));
  for (const [name, g] of ordered) {
    const key = `${main.has(name)}-${g}`;
    const s = groups.get(key) ?? { names: [], greenS: g };
    s.names.push(name);
    groups.set(key, s);
  }
  return [...groups.values()];
}

/** SVG arc path on a circle of radius r centred at (c, c), from fraction f0 to f1 of the cycle. */
function arc(c: number, r: number, f0: number, f1: number) {
  const a0 = f0 * 2 * Math.PI - Math.PI / 2;
  const a1 = f1 * 2 * Math.PI - Math.PI / 2;
  const large = f1 - f0 > 0.5 ? 1 : 0;
  return `M ${c + r * Math.cos(a0)} ${c + r * Math.sin(a0)} A ${r} ${r} 0 ${large} 1 ${c + r * Math.cos(a1)} ${c + r * Math.sin(a1)}`;
}

export function PhaseRing({ cycleS, stages, label }: { cycleS: number; stages: Stage[]; label: string }) {
  const { t } = useT();
  const green = stages.reduce((a, s) => a + s.greenS, 0);
  const inter = stages.length ? Math.max(0, cycleS - green) / stages.length : 0;
  const size = 220;
  const c = size / 2;
  const r = 84;
  let at = 0; // seconds into the cycle
  const arcs = stages.map((s, i) => {
    const g = { from: at / cycleS, to: (at + s.greenS) / cycleS, colour: SERIES[i % SERIES.length]! };
    at += s.greenS;
    const ig = { from: at / cycleS, to: (at + inter) / cycleS };
    at += inter;
    return { stage: s, g, ig };
  });
  return (
    <div className="flex flex-wrap items-center gap-5">
      <svg viewBox={`0 0 ${size} ${size}`} className="w-[200px] shrink-0" role="img" aria-label={label}>
        <circle cx={c} cy={c} r={r} fill="none" stroke="var(--grid)" strokeWidth="24" />
        {arcs.map(({ g, ig }, i) => (
          <g key={i}>
            <path d={arc(c, r, g.from, Math.max(g.from + 0.001, g.to - 0.003))} fill="none" stroke={g.colour} strokeWidth="24" />
            {ig.to > ig.from && <path d={arc(c, r, ig.from, ig.to)} fill="none" stroke="#ffb020" strokeOpacity="0.7" strokeWidth="10" />}
          </g>
        ))}
        {/* tick at the start of the cycle (stage 1 green begins) */}
        <line x1={c} x2={c} y1={c - r - 16} y2={c - r + 16} stroke="var(--ink)" strokeWidth="2" />
        <text x={c} y={c - 2} textAnchor="middle" fontSize="30" fontWeight="700" fill="var(--ink)" className="num">{num(cycleS)}</text>
        <text x={c} y={c + 20} textAnchor="middle" fontSize="12" fill="var(--ink-3)">{t.junction.perCycle}</text>
      </svg>
      <ol className="flex min-w-0 flex-col gap-2 text-sm">
        {arcs.map(({ stage, g }, i) => (
          <li key={i} className="flex items-start gap-2">
            <span aria-hidden className="mt-1 size-3 shrink-0 rounded-sm" style={{ background: g.colour }} />
            <span className="min-w-0">
              <span className="num font-semibold">{num(stage.greenS)} s</span> <span className="muted">{stage.names.join(" + ")}</span>
            </span>
          </li>
        ))}
        {inter > 0 && (
          <li className="faint flex items-center gap-2 text-xs">
            <span aria-hidden className="h-1.5 w-3 shrink-0 rounded-sm bg-[#ffb020]/70" /> {fmt(t.junction.intergreen, { s: num(inter, 1), n: stages.length })}
          </li>
        )}
      </ol>
    </div>
  );
}
