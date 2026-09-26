"use client";
// Frame for the website's text pages (pricing, security, status, contact): brand, page links,
// language switch that keeps the page, theme toggle, and the same footer notes as the story.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { useEffect, useState, type ReactNode } from "react";
import type { Locale, Messages } from "@/lib/i18n";

const PAGES = [["pricing", "pricing"], ["security", "security"], ["status", "status"], ["contact", "contact"]] as const;

export function SubPage({ locale, t, title, lead, children }: { locale: Locale; t: Messages; title: string; lead?: string; children: ReactNode }) {
  const path = usePathname();
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const other = locale === "en" ? "hi" : "en";
  const rest = path.split("/").slice(2).join("/");
  const dark = resolvedTheme !== "light";
  return (
    <div className="min-h-dvh bg-[var(--bg)] text-[var(--ink)]">
      <header className="mx-3 mt-3 flex max-w-5xl flex-wrap items-center justify-between gap-3 rounded-2xl px-4 py-2 surface xl:mx-auto">
        <Link href={`/${locale}`} className="flex items-center gap-2" aria-label="HariBatti">
          <svg viewBox="0 0 24 48" className="h-7 w-3.5" aria-hidden><rect width="24" height="48" rx="12" fill="currentColor" opacity=".18" /><circle cx="12" cy="12" r="6" fill="#ff3b30" opacity=".35" /><circle cx="12" cy="24" r="6" fill="#ffb020" opacity=".35" /><circle cx="12" cy="36" r="6" fill="#22c55e" /></svg>
          <span className="display text-lg font-semibold">HariBatti</span>
        </Link>
        <nav aria-label={t.pages.home} className="flex flex-wrap items-center gap-4 text-sm">
          {PAGES.map(([slug, key]) => (
            <Link key={slug} href={`/${locale}/${slug}`} aria-current={rest === slug ? "page" : undefined} className={`hover:text-[var(--accent)] ${rest === slug ? "font-semibold text-[var(--accent)]" : ""}`}>{t.pages[key]}</Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Link href={`/${other}/${rest}`} hrefLang={other} lang={other} aria-label={t.nav.langLabel} className="rounded-full border border-[var(--line)] px-3 py-1.5 text-sm font-semibold hover:border-[var(--accent)]">{t.nav.lang}</Link>
          <button type="button" onClick={() => setTheme(dark ? "light" : "dark")} aria-label={t.nav.theme} className="grid size-9 place-items-center rounded-full border border-[var(--line)] hover:border-[var(--accent)]">
            {mounted && <span aria-hidden className="text-sm">{dark ? "☀" : "☾"}</span>}
          </button>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-5xl px-4 py-12 sm:py-16">
        <Link href={`/${locale}`} className="text-sm text-[var(--ink-2)] hover:text-[var(--accent)]">← {t.pages.back}</Link>
        <h1 className="display mt-4 text-4xl font-semibold sm:text-5xl">{title}</h1>
        {lead && <p className="mt-4 max-w-2xl text-lg text-[var(--ink-2)]">{lead}</p>}
        <div className="mt-10">{children}</div>
      </main>
      <footer className="border-t border-[var(--line)] px-4 py-8 text-sm text-[var(--ink-2)]">
        <div className="mx-auto grid max-w-5xl gap-2">
          <p>{t.footer.affiliation}</p>
          <p>{t.footer.privacy}</p>
          <p>© 2026 HariBatti</p>
        </div>
      </footer>
    </div>
  );
}
