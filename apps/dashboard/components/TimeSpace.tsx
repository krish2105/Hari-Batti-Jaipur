"use client";
// Time-space diagram for the main road. Time runs left → right, distance top (J08, Mansarovar
// Metro end) → bottom (J03, Sanganer Stadium end). Each junction is a bar that is green while the
// main road has green and red otherwise. The white line is one car driving east at the chosen speed:
// a flat step means it waits at a red.
import { drive, greenWindows, type TsJunction } from "@/lib/timespace";
import { num, useT } from "@/lib/i18n";

export function TimeSpace({ js, speedMs, horizonS = 360, label }: { js: TsJunction[]; speedMs: number; horizonS?: number; label: string }) {
  const { t } = useT();
  const W = 900;
  const H = 60 + js.length * 56;
  const left = 64;
  const right = 16;
  const top = 26;
  const maxX = Math.max(1, ...js.map((j) => j.x));
  const tx = (s: number) => left + (s / horizonS) * (W - left - right);
  const dy = (x: number) => top + (x / maxX) * (H - top - 40);
  const car = drive(js, speedMs);
  const path = car.pts.filter(([, s]) => s <= horizonS * 1.5).map(([x, s], i) => `${i ? "L" : "M"} ${tx(s)} ${dy(x)}`).join(" ");
  const ticks = Array.from({ length: Math.floor(horizonS / 60) + 1 }, (_, i) => i * 60);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[640px]" role="img" aria-label={label}>
      <defs>
        <clipPath id="ts-clip"><rect x={left} y={0} width={W - left - right} height={H} /></clipPath>
      </defs>
      {ticks.map((s) => (
        <g key={s}>
          <line x1={tx(s)} x2={tx(s)} y1={top - 8} y2={H - 30} stroke="var(--grid)" />
          <text x={tx(s)} y={H - 12} textAnchor="middle" fontSize="11" fill="var(--ink-3)" className="num">{s} s</text>
        </g>
      ))}
      {js.map((j) => (
        <g key={j.id}>
          <text x={left - 10} y={dy(j.x) + 4} textAnchor="end" fontSize="12" fontWeight="700" fill="var(--ink)">{j.id}</text>
          <rect x={left} y={dy(j.x) - 5} width={W - left - right} height={10} rx={2} fill="#ff3b30" fillOpacity="0.55" />
          {greenWindows(j, 0, horizonS).map(([a, b]) => (
            <rect key={a} x={tx(a)} y={dy(j.x) - 5} width={Math.max(1, tx(b) - tx(a))} height={10} rx={2} fill="#22c55e" />
          ))}
        </g>
      ))}
      <path d={path} clipPath="url(#ts-clip)" fill="none" stroke="var(--ink)" strokeWidth="2.5" strokeLinejoin="round" />
      <text x={W - right} y={14} textAnchor="end" fontSize="12" fill="var(--ink-2)">
        {t.plans.tsStops}: <tspan fontWeight="700" fill="var(--ink)">{car.stops}</tspan> · {num(car.travelS)} s
      </text>
    </svg>
  );
}
