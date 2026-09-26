"use client";
// Schematic corridor strip (works offline): the six main-road junctions in order, 500 m apart
// (ASSUMED), each dot coloured by Health for the selected hours, plus the separate B2 Bypass pair.
import Link from "next/link";
import { CORRIDOR, B2_PAIR, healthColour } from "@/lib/health";
import { num, useT } from "@/lib/i18n";
import type { JunctionInfo } from "@/lib/types";

export function CorridorSchematic({ health, byId }: { health: Record<string, number | null>; byId: Record<string, JunctionInfo> }) {
  const { t, href } = useT();
  const W = 1000;
  const x = (i: number) => 70 + i * ((W - 140) / (CORRIDOR.length - 1));
  const node = (id: string, cx: number, cy: number) => {
    const h = health[id];
    const name = byId[id]?.name.replace(/ Junction$/, "") ?? id;
    return (
      <Link key={id} href={href(`/junction/${id}`)} aria-label={`${id} ${name}: ${t.metric.health} ${num(h)}`}>
        <g className="cursor-pointer [&:hover_circle.ring]:opacity-100">
          <line x1={cx} x2={cx} y1={cy - 34} y2={cy + 34} stroke="var(--line)" strokeWidth="6" strokeLinecap="round" />
          <circle className="ring opacity-0 transition-opacity" cx={cx} cy={cy} r="21" fill="none" stroke="var(--accent)" strokeWidth="2" />
          <circle cx={cx} cy={cy} r="15" fill="var(--panel)" stroke={healthColour(h)} strokeWidth="4" />
          <text x={cx} y={cy + 4} textAnchor="middle" fontSize="11" fontWeight="700" fill="var(--ink)" className="num">{h === null || h === undefined ? "—" : Math.round(h)}</text>
          <text x={cx} y={cy - 44} textAnchor="middle" fontSize="13" fontWeight="700" fill="var(--ink)">{id}</text>
          <text x={cx} y={cy + 54} textAnchor="middle" fontSize="11" fill="var(--ink-2)">{name}</text>
        </g>
      </Link>
    );
  };
  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${W} 320`} className="min-w-[620px]" role="img" aria-label={t.overview.schematic}>
        <text x="10" y="112" fontSize="11" fill="var(--ink-3)">Metro</text>
        <text x={W - 10} y="112" fontSize="11" fill="var(--ink-3)" textAnchor="end">Stadium</text>
        <line x1="40" x2={W - 40} y1="100" y2="100" stroke="var(--ink-3)" strokeOpacity="0.5" strokeWidth="10" strokeLinecap="round" />
        <line x1="40" x2={W - 40} y1="100" y2="100" stroke="var(--panel)" strokeWidth="1.2" strokeDasharray="10 12" />
        {CORRIDOR.map((id, i) => i > 0 && (
          <text key={`d${id}`} x={(x(i) + x(i - 1)) / 2} y="92" textAnchor="middle" fontSize="10" fill="var(--ink-3)">500 m*</text>
        ))}
        {CORRIDOR.map((id, i) => node(id, x(i), 100))}
        <line x1="70" x2="300" y1="255" y2="255" stroke="var(--ink-3)" strokeOpacity="0.35" strokeWidth="8" strokeLinecap="round" strokeDasharray="1 14" />
        {B2_PAIR.map((id, i) => (
          <g key={id}>{node(id, 110 + i * 150, 255)}</g>
        ))}
        <text x="330" y="259" fontSize="11" fill="var(--ink-3)">{t.common.b2}</text>
      </svg>
      <p className="faint mt-1 text-xs">* {t.overview.schematicNote}</p>
    </div>
  );
}
