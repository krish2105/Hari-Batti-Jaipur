// Source badge: every number on the site says where it came from (SIM, SURVEY, ASSUMED, ESTIMATE...).
import type { Messages } from "@/lib/i18n";

const TONE: Record<string, string> = {
  SIM: "border-[#7B61FF]/50 text-[#6b52e8] dark:text-[#b3a5ff] bg-[#7B61FF]/10",
  SURVEY: "border-[#3f7d3a]/40 text-[#2f6a2a] dark:text-[#9fd49a] bg-[#6A994E]/10",
  ASSUMED: "border-[var(--accent)]/40 text-[var(--accent)] bg-[var(--accent-2)]/10",
  ESTIMATE: "border-[var(--ink-2)]/30 text-[var(--ink-2)] bg-[var(--ink)]/5",
  FIELD: "border-[#0081A7]/40 text-[#0081A7] bg-[#0081A7]/10",
  ITMS: "border-[#3b82f6]/40 text-[#3b82f6] bg-[#3b82f6]/10",
  CROWD: "border-[#F77F00]/40 text-[#c56600] bg-[#F77F00]/10",
};

export function SourceBadge({ kind, t, className = "" }: { kind: keyof Messages["badge"]; t: Messages["badge"]; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold tracking-wide whitespace-nowrap ${TONE[kind] ?? TONE.ESTIMATE} ${className}`}>
      <span aria-hidden className="size-1.5 rounded-full bg-current opacity-70" />
      {t[kind]}
    </span>
  );
}
