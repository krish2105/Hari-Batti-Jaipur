"use client";
// One-click "useful / not useful" on an insight (P8 W13). Votes go to the current tenant's pilot
// feedback; voting again changes the vote. The counts appear in the pilot page and evidence pack.
import { useState } from "react";
import { usePathname } from "next/navigation";
import { usePilot } from "@/lib/pilot";
import { useT } from "@/lib/i18n";

export function Useful({ insight }: { insight: string }) {
  const { t } = useT();
  const { mine, vote } = usePilot();
  const path = usePathname();
  const [err, setErr] = useState(false);
  const current = mine[insight];
  const send = async (useful: boolean) => {
    setErr(false);
    try {
      await vote(insight, useful, path.split("/").slice(2).join("/") || "overview");
    } catch {
      setErr(true);
    }
  };
  const btn = (on: boolean, useful: boolean, label: string, icon: string) => (
    <button
      type="button"
      aria-pressed={on}
      aria-label={label}
      title={label}
      onClick={() => send(useful)}
      className={`rounded-full border px-2 py-0.5 text-xs leading-5 transition ${on ? (useful ? "border-[#16a34a] bg-[#16a34a]/15 text-[#16a34a]" : "border-[#ff3b30] bg-[#ff3b30]/10 text-[#ff3b30]") : "border-[var(--line)] faint hover:border-[var(--accent)]"}`}
    >
      <span aria-hidden>{icon}</span>
    </button>
  );
  return (
    <span className="no-print inline-flex items-center gap-1" role="group" aria-label={t.pilot.usefulQ}>
      {btn(current === true, true, t.pilot.useful, "👍")}
      {btn(current === false, false, t.pilot.notUseful, "👎")}
      {err && <span className="text-[10px] text-[#ff3b30]">{t.pilot.voteFailed}</span>}
    </span>
  );
}
