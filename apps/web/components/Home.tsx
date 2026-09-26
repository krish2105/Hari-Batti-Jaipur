"use client";
// The whole scroll story: one fixed 3D canvas behind ten sections of real HTML.
import dynamic from "next/dynamic";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Header } from "@/components/ui/Header";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { Ai, Hero, Itms, Solution, Squeeze, Wait } from "@/components/sections/Story";
import { MapSection } from "@/components/sections/MapSection";
import { Wave } from "@/components/sections/Wave";
import { Mix } from "@/components/sections/Mix";
import { Impact } from "@/components/sections/Impact";
import { Pilot } from "@/components/sections/Pilot";
import type { Locale, Messages } from "@/lib/i18n";
import { measure } from "@/lib/scrollStore";
import { DAY, site } from "@/lib/site";
import { useSignals } from "@/lib/useSignals";

const Scene = dynamic(() => import("@/components/three/Scene"), { ssr: false });

function hasWebGL() {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

/** Traffic density for the current hour in India, from the survey's hourly PCU profile (0.3–1). */
function densityNow() {
  const hourIst = (new Date().getUTCHours() + 5 + (new Date().getUTCMinutes() + 30 >= 60 ? 1 : 0)) % 24;
  const h = (hourIst - 8 + 24) % 24;
  const total = (i: number) => site.junctions.reduce((s, j) => s + (j.hourlyPcu[i] ?? 0), 0);
  const max = Math.max(...Array.from({ length: 24 }, (_, i) => total(i)));
  return { density: Math.max(0.45, total(h) / max), hour: `${String(hourIst).padStart(2, "0")}:00` };
}

export function Home({ locale, t }: { locale: Locale; t: Messages }) {
  const { states } = useSignals();
  const { resolvedTheme } = useTheme();
  const dark = resolvedTheme !== "light";
  const [webgl, setWebgl] = useState<boolean | null>(null);
  const [start3d, setStart3d] = useState(false);
  const [quality, setQuality] = useState<"high" | "low">("high");
  const [d, setD] = useState({ density: 0.8, hour: "18:00" }); // replaced by the real India hour after mount

  useEffect(() => {
    setWebgl(hasWebGL());
    setD(densityNow());
    // Progressive enhancement: phones and weak devices start the 3D city on the first scroll or
    // touch (the hero text is already readable on the static backdrop); desktops when the browser
    // is idle. Keeps the first paint fast and the main thread free.
    const weak = window.matchMedia("(max-width: 767px)").matches || (navigator.hardwareConcurrency ?? 8) < 6;
    let cancelIdle = () => {};
    const go = () => setStart3d(true);
    const events = ["pointerdown", "touchstart", "keydown", "wheel", "scroll"] as const;
    events.forEach((e) => window.addEventListener(e, go, { once: true, passive: true }));
    if (!weak) {
      const ric = (window as Window & { requestIdleCallback?: (cb: () => void, o?: { timeout: number }) => number }).requestIdleCallback;
      if (ric) {
        const id = ric(go, { timeout: 2000 });
        cancelIdle = () => (window as Window & { cancelIdleCallback?: (i: number) => void }).cancelIdleCallback?.(id);
      } else {
        const id = window.setTimeout(go, 1200);
        cancelIdle = () => window.clearTimeout(id);
      }
    }
    const on = () => measure();
    on();
    window.addEventListener("scroll", on, { passive: true });
    window.addEventListener("resize", on);
    return () => {
      window.removeEventListener("scroll", on);
      window.removeEventListener("resize", on);
      cancelIdle();
    };
  }, []);

  return (
    <>
      <Header locale={locale} t={t.nav} />
      <div className="fixed inset-0 -z-0" aria-hidden>
        {/* instant, static backdrop while the 3D scene loads (and if WebGL is missing) */}
        <div className="absolute inset-0 bg-[radial-gradient(120%_80%_at_70%_20%,#fff1e8_0%,#f3cdbf_65%)] dark:bg-[radial-gradient(120%_80%_at_70%_20%,#2a2f4a_0%,#0f1b2d_60%)]" />
        {webgl && start3d && <div className="absolute inset-0"><Scene states={states} dark={dark} density={d.density} onQuality={setQuality} /></div>}
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgb(247_228_221/0.55),transparent_60%)] dark:bg-[linear-gradient(90deg,rgb(15_27_45/0.55),transparent_60%)]" />
        <div className="absolute inset-0 bg-[rgb(247_228_221/0.55)] sm:hidden dark:bg-[rgb(15_27_45/0.5)]" />
      </div>
      <main id="main" className="relative z-10">
        <Hero t={t} states={states} />
        <Wait t={t} />
        <Squeeze t={t} />
        <Mix t={t} dark={dark} />
        <MapSection t={t} states={states} dark={dark} />
        <Itms t={t} />
        <Solution t={t} states={states} />
        <Wave t={t} />
        <Ai t={t} />
        <Impact t={t} />
        <Pilot t={t} />
      </main>
      <div className="pointer-events-none fixed bottom-3 right-3 z-20 hidden gap-2 sm:flex">
        <SourceBadge kind="SIM" t={t.badge} className="surface" />
        <span className="surface rounded-full px-2 py-0.5 text-[11px] text-[var(--ink-2)]">{d.hour} · {t.badge.SURVEY} ({DAY.slice(8)} May)</span>
        {quality === "low" && <span className="surface rounded-full px-2 py-0.5 text-[11px] text-[var(--ink-2)]">{t.quality.low}</span>}
      </div>
    </>
  );
}
