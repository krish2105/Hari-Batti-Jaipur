"use client";
// Top bar: brand, section links, language switch (keeps the section), light/dark toggle.
import Link from "next/link";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import type { Locale, Messages } from "@/lib/i18n";

export function Header({ locale, t }: { locale: Locale; t: Messages["nav"] }) {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [hash, setHash] = useState("");
  useEffect(() => {
    setMounted(true);
    const on = () => setHash(window.location.hash);
    on();
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  const other = locale === "en" ? "hi" : "en";
  const dark = resolvedTheme !== "light";
  return (
    <header className="fixed inset-x-0 top-0 z-40">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 rounded bg-[var(--ink)] px-3 py-2 text-[var(--bg)]">{t.skip}</a>
      <div className="mx-3 mt-3 flex max-w-6xl items-center justify-between gap-3 rounded-2xl px-3 py-2 surface sm:px-4 xl:mx-auto">
        <Link href={`/${locale}`} className="flex items-center gap-2" aria-label="HariBatti">
          <svg viewBox="0 0 24 48" className="h-7 w-3.5" aria-hidden><rect width="24" height="48" rx="12" fill="currentColor" opacity=".18" /><circle cx="12" cy="12" r="6" fill="#ff3b30" opacity=".35" /><circle cx="12" cy="24" r="6" fill="#ffb020" opacity=".35" /><circle cx="12" cy="36" r="6" fill="#22c55e" /></svg>
          <span className="display text-lg font-semibold">HariBatti</span>
        </Link>
        <nav className="hidden items-center gap-5 text-sm md:flex" aria-label="Sections">
          <a href="#map" className="hover:text-[var(--accent)]">{t.map}</a>
          <a href="#wave" className="hover:text-[var(--accent)]">{t.demo}</a>
          <a href="#evidence" className="hover:text-[var(--accent)]">{t.evidence}</a>
          <a href="#impact" className="hover:text-[var(--accent)]">{t.impact}</a>
          <a href="#pilot" className="hover:text-[var(--accent)]">{t.pilot}</a>
        </nav>
        <div className="flex items-center gap-2">
          <Link href={`/${other}${hash}`} hrefLang={other} lang={other} aria-label={t.langLabel}
            className="rounded-full border border-[var(--line)] px-3 py-1.5 text-sm font-semibold hover:border-[var(--accent)]">
            {t.lang}
          </Link>
          <button type="button" onClick={() => setTheme(dark ? "light" : "dark")} aria-label={t.theme} title={t.theme}
            className="grid size-9 place-items-center rounded-full border border-[var(--line)] hover:border-[var(--accent)]">
            {mounted && (dark ? (
              <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
            ) : (
              <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></svg>
            ))}
          </button>
        </div>
      </div>
    </header>
  );
}
