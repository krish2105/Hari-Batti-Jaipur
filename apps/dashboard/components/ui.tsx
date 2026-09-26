"use client";
// Small building blocks used on every screen: source badges, KPI tiles, section cards,
// loading / error / pending states, the LED countdown and segmented tabs.
import type { ReactNode } from "react";
import { fmt, useT, type Messages } from "@/lib/i18n";
import { SIGNAL_HEX } from "@/lib/health";
import type { ApiError } from "@/lib/api";
import type { Colour } from "@/lib/types";

const TONE: Record<string, string> = {
  SIM: "border-[#7B61FF]/50 text-[#5b43d6] dark:text-[#b3a5ff] bg-[#7B61FF]/10",
  SURVEY: "border-[#3f7d3a]/40 text-[#2f6a2a] dark:text-[#9fd49a] bg-[#6A994E]/10",
  ASSUMED: "border-[var(--accent)]/40 text-[var(--accent)] bg-[var(--accent-soft)]",
  ESTIMATE: "border-[var(--ink-3)]/40 text-[var(--ink-2)] bg-[var(--ink)]/5",
  MODEL: "border-[#0081A7]/40 text-[#006b8a] dark:text-[#6fd0ec] bg-[#0081A7]/10",
  FIELD: "border-[#0081A7]/40 text-[#006b8a] dark:text-[#6fd0ec] bg-[#0081A7]/10",
  ITMS: "border-[#3b82f6]/40 text-[#2563eb] dark:text-[#93b8ff] bg-[#3b82f6]/10",
  CROWD: "border-[#F77F00]/40 text-[#b35c00] dark:text-[#ffb366] bg-[#F77F00]/10",
};

export type BadgeKind = keyof Messages["badge"];

/** Every number on screen carries one of these: where it came from. */
export function Badge({ kind, className = "" }: { kind: BadgeKind; className?: string }) {
  const { t } = useT();
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap ${TONE[kind] ?? TONE.ESTIMATE} ${className}`}>
      <span aria-hidden className="size-1.5 rounded-full bg-current opacity-70" />
      {t.badge[kind]}
    </span>
  );
}

/** Badges for a source string from the API, e.g. "SURVEY counts + ASSUMED timing". */
export function SourceBadges({ source }: { source: string | undefined }) {
  if (!source) return null;
  const kinds = (["SIM", "SURVEY", "ASSUMED", "FIELD", "ITMS", "CROWD"] as const).filter((k) => source.includes(k));
  return (
    <span className="inline-flex flex-wrap gap-1">
      {kinds.map((k) => (
        <Badge key={k} kind={k} />
      ))}
    </span>
  );
}

export function PageHead({ title, lead, children }: { title: string; lead?: string; children?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-3xl">
        <h1 className="text-2xl font-semibold tracking-tight md:text-[1.75rem]">{title}</h1>
        {lead && <p className="muted mt-1.5 text-sm leading-relaxed md:text-[0.95rem]">{lead}</p>}
      </div>
      {children && <div className="no-print flex flex-wrap items-center gap-2">{children}</div>}
    </header>
  );
}

export function Card({ title, badge, action, children, className = "", id }: { title?: ReactNode; badge?: ReactNode; action?: ReactNode; children: ReactNode; className?: string; id?: string }) {
  return (
    <section id={id} className={`panel p-4 md:p-5 ${className}`}>
      {(title || badge || action) && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            {title && <h2 className="text-[0.95rem] font-semibold">{title}</h2>}
            {badge}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Kpi({ label, value, unit, badge, hint, tone }: { label: string; value: ReactNode; unit?: string; badge?: ReactNode; hint?: string; tone?: string }) {
  return (
    <div className="panel flex min-w-0 flex-col gap-2 p-4">
      <span className="eyebrow">{label}</span>
      <span className="num text-2xl font-semibold leading-none md:text-[1.7rem]" style={tone ? { color: tone } : undefined}>
        {value}
        {unit && <span className="faint ml-1 text-sm font-normal">{unit}</span>}
      </span>
      <span className="flex flex-wrap items-center gap-1.5">
        {badge}
        {hint && <span className="faint text-xs">{hint}</span>}
      </span>
    </div>
  );
}

export function Loading() {
  const { t } = useT();
  return (
    <div role="status" className="faint flex items-center gap-2 p-4 text-sm">
      <span className="live-dot size-2 rounded-full bg-[var(--accent)]" /> {t.common.loading}
    </div>
  );
}

export function ErrorNote({ error }: { error: ApiError | null }) {
  const { t } = useT();
  if (!error) return null;
  return (
    <p role="alert" className="rounded-lg border border-[#ff3b30]/40 bg-[#ff3b30]/10 p-3 text-sm">
      {fmt(t.common.error, { msg: error.message })}
    </p>
  );
}

export function Pending({ what }: { what: string }) {
  const { t } = useT();
  return (
    <div className="rounded-xl border border-dashed border-[var(--line)] p-5 text-sm">
      <p className="font-semibold">{t.common.pending}</p>
      <p className="muted mt-1">{fmt(t.common.pendingBody, { what })}</p>
    </div>
  );
}

/** Dot-matrix countdown like Jaipur's signal heads. The colour name is always printed too. */
export function Led({ colour, seconds, size = "md" }: { colour: Colour; seconds: number; size?: "sm" | "md" }) {
  const { t } = useT();
  const hex = SIGNAL_HEX[colour];
  const text = String(Math.min(999, Math.max(0, Math.round(seconds)))).padStart(2, "0");
  return (
    <span className="inline-flex items-baseline gap-1.5">
      <span className={`led relative leading-none ${size === "md" ? "text-4xl" : "text-2xl"}`} style={{ color: hex, textShadow: `0 0 14px ${hex}77` }}>
        <span aria-hidden className="absolute inset-0 select-none" style={{ color: "var(--led-off)", textShadow: "none" }}>
          {"8".repeat(text.length)}
        </span>
        <span className="relative">{text}</span>
      </span>
      <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: hex }}>
        {t.signal[colour]}
        <span className="sr-only"> {seconds} {t.signal.seconds}</span>
      </span>
    </span>
  );
}

/** Segmented control (radio-like). */
export function Segmented<T extends string>({ value, options, onChange, label }: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="panel-2 inline-flex flex-wrap gap-0.5 p-0.5">
      {options.map((o) => (
        <button key={o.value} type="button" role="radio" aria-checked={value === o.value} className="tab" onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
