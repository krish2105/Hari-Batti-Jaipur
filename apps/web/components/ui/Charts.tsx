"use client";
// Small, dependency-free SVG charts for the Evidence section. Every mark is keyboard-focusable and
// has a text label (hover or focus shows the exact value), so the charts work without a mouse and
// for screen readers. Colours follow the site tokens; signal colours are not used for decoration.
import { useId, useState, type ReactNode } from "react";

export type Bar = { key: string; label: string; value: number; ci?: number | null; note?: string; strong?: boolean; muted?: boolean };

/** Horizontal bars with optional 95% CI whiskers and a reference line (e.g. a target). */
export function Bars({ rows, format, max, refValue, refLabel, lowerIsBetter }: {
  rows: Bar[]; format: (v: number) => string; max?: number; refValue?: number; refLabel?: string; lowerIsBetter?: boolean;
}) {
  const [hover, setHover] = useState<string | null>(null);
  const top = max ?? Math.max(...rows.map((r) => r.value + (r.ci ?? 0)), refValue ?? 0) * 1.08;
  const pct = (v: number) => `${Math.max(0, Math.min(100, (v / (top || 1)) * 100))}%`;
  return (
    <div className="relative">
      <ul className="grid gap-2.5">
        {rows.map((r) => {
          const on = hover === r.key;
          return (
            <li key={r.key}>
              <button type="button" className="group block w-full text-left" onMouseEnter={() => setHover(r.key)} onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(r.key)} onBlur={() => setHover(null)} aria-label={`${r.label}: ${format(r.value)}${r.ci ? ` ± ${format(r.ci)}` : ""}${r.note ? `, ${r.note}` : ""}`}>
                <span className="flex items-baseline justify-between gap-3 text-sm">
                  <span className={`truncate ${r.strong ? "font-semibold" : ""} ${r.muted ? "text-[var(--ink-2)]" : ""}`}>{r.label}</span>
                  <span className="led shrink-0 tabular-nums">{format(r.value)}{r.ci ? <span className="text-[var(--ink-2)]"> ±{format(r.ci)}</span> : null}</span>
                </span>
                <span className="relative mt-1 block h-3 rounded-full bg-[var(--ink)]/8">
                  <span className={`absolute inset-y-0 left-0 rounded-full transition-[width,opacity] duration-500 ${r.strong ? "bg-[var(--accent)]" : "bg-[var(--accent-2)]/60"} ${on ? "opacity-100" : "opacity-90"}`}
                    style={{ width: pct(r.value) }} />
                  {r.ci ? (
                    <span aria-hidden className="absolute top-1/2 h-2 -translate-y-1/2 border-x-2 border-[var(--ink)]/60"
                      style={{ left: pct(Math.max(0, r.value - r.ci)), width: `calc(${pct(r.value + r.ci)} - ${pct(Math.max(0, r.value - r.ci))})` }}>
                      <span className="absolute inset-x-0 top-1/2 h-px bg-[var(--ink)]/60" />
                    </span>
                  ) : null}
                  {refValue !== undefined && <span aria-hidden className="absolute -inset-y-1 w-0.5 bg-[var(--ink)]" style={{ left: pct(refValue) }} />}
                </span>
                {on && r.note && <span className="mt-1 block text-xs text-[var(--ink-2)]">{r.note}</span>}
              </button>
            </li>
          );
        })}
      </ul>
      {(refLabel || lowerIsBetter !== undefined) && (
        <p className="mt-3 flex flex-wrap gap-x-4 text-xs text-[var(--ink-2)]">
          {refLabel && <span><span aria-hidden className="mr-1 inline-block h-3 w-0.5 translate-y-0.5 bg-[var(--ink)]" />{refLabel}</span>}
        </p>
      )}
    </div>
  );
}

export type Point = { key: string; x: number; y: number; r?: number; label: string; strong?: boolean };

/** Scatter (0-1 axes shown as %) with a target box; hover or focus a point for its label. */
export function Scatter({ points, xLabel, yLabel, target, caption }: { points: Point[]; xLabel: string; yLabel: string; target?: number; caption?: ReactNode }) {
  const id = useId();
  const [sel, setSel] = useState<Point | null>(null);
  const W = 420, H = 300, L = 44, B = 36, T = 10, R = 10;
  const x = (v: number) => L + v * (W - L - R);
  const y = (v: number) => H - B - v * (H - B - T);
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  return (
    <figure>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="group" aria-labelledby={`${id}-cap`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={x(0)} x2={x(1)} y1={y(t)} y2={y(t)} stroke="currentColor" strokeOpacity="0.1" />
            <line x1={x(t)} x2={x(t)} y1={y(0)} y2={y(1)} stroke="currentColor" strokeOpacity="0.1" />
            <text x={L - 6} y={y(t) + 4} textAnchor="end" fontSize="11" fill="currentColor" opacity="0.6">{t * 100}%</text>
            <text x={x(t)} y={H - B + 16} textAnchor="middle" fontSize="11" fill="currentColor" opacity="0.6">{t * 100}%</text>
          </g>
        ))}
        {target !== undefined && (
          <rect x={x(target)} y={y(1)} width={x(1) - x(target)} height={y(target) - y(1)} fill="#22c55e" fillOpacity="0.12" stroke="#22c55e" strokeOpacity="0.5" strokeDasharray="4 4" />
        )}
        <text x={(x(0) + x(1)) / 2} y={H - 4} textAnchor="middle" fontSize="12" fill="currentColor">{xLabel}</text>
        <text x={12} y={(y(0) + y(1)) / 2} textAnchor="middle" fontSize="12" fill="currentColor" transform={`rotate(-90 12 ${(y(0) + y(1)) / 2})`}>{yLabel}</text>
        {points.map((p) => (
          <circle key={p.key} cx={x(p.x)} cy={y(p.y)} r={p.r ?? 6} tabIndex={0} role="img" aria-label={p.label}
            fill={p.strong ? "var(--accent)" : "var(--accent-2)"} fillOpacity={p.strong ? 1 : 0.55} stroke={sel?.key === p.key ? "var(--ink)" : "none"} strokeWidth="2"
            onMouseEnter={() => setSel(p)} onMouseLeave={() => setSel(null)} onFocus={() => setSel(p)} onBlur={() => setSel(null)} className="cursor-pointer outline-none" />
        ))}
      </svg>
      <figcaption id={`${id}-cap`} className="mt-1 min-h-10 text-xs text-[var(--ink-2)]">{sel ? <b className="text-[var(--ink)]">{sel.label}</b> : caption}</figcaption>
    </figure>
  );
}

/** A labelled 0-100% meter, e.g. achieved vs target coverage. */
export function Meter({ value, target, label }: { value: number; target?: number; label: string }) {
  return (
    <div role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value * 100)} aria-label={label}>
      <div className="relative h-3 rounded-full bg-[var(--ink)]/8">
        <div className="absolute inset-y-0 left-0 rounded-full bg-[var(--accent)]" style={{ width: `${Math.min(100, value * 100)}%` }} />
        {target !== undefined && <div aria-hidden className="absolute -inset-y-1 w-0.5 bg-[var(--ink)]" style={{ left: `${target * 100}%` }} />}
      </div>
    </div>
  );
}

/** Tabs (ARIA tablist) that switch panels without reloading. */
export function Tabs<T extends string>({ value, onChange, options, label }: { value: T; onChange: (v: T) => void; options: { value: T; label: string }[]; label: string }) {
  return (
    <div role="tablist" aria-label={label} className="surface inline-flex max-w-full flex-wrap gap-1 rounded-full p-1">
      {options.map((o) => (
        <button key={o.value} type="button" role="tab" aria-selected={value === o.value} onClick={() => onChange(o.value)}
          className={`rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${value === o.value ? "bg-[var(--ink)] text-[var(--bg)]" : "text-[var(--ink-2)] hover:text-[var(--ink)]"}`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
