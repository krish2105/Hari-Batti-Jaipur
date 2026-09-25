// The signature: the LED dot-matrix countdown Jaipur signals carry. Colour is never the only cue —
// the colour name is always printed next to the number.
import type { SignalColour } from "@haribatti/core";
import type { Messages } from "@/lib/i18n";

const HEX: Record<SignalColour, string> = { RED: "#ff3b30", AMBER: "#ffb020", GREEN: "#22c55e", FLASHING_AMBER: "#ffb020" };

export function LedCountdown({ colour, seconds, t, size = "md" }: { colour: SignalColour; seconds: number; t: Messages["signal"]; size?: "sm" | "md" | "xl" }) {
  const text = String(Math.min(999, Math.max(0, seconds))).padStart(2, "0");
  const cls = size === "xl" ? "text-[clamp(4.5rem,15vw,10rem)]" : size === "md" ? "text-5xl" : "text-2xl";
  return (
    <span className="inline-flex items-baseline gap-2" aria-live="off">
      <span className={`led relative leading-none ${cls}`} style={{ color: HEX[colour], textShadow: `0 0 18px ${HEX[colour]}88` }}>
        <span aria-hidden className="absolute inset-0 select-none" style={{ color: "var(--led-off)", textShadow: "none" }}>88</span>
        <span className="relative">{text}</span>
      </span>
      <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: HEX[colour] }}>
        {t[colour]} <span className="sr-only">{seconds} {t.seconds}</span>
      </span>
    </span>
  );
}
