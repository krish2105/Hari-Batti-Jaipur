"use client";
// The app frame: sidebar navigation, top bar (API + signal-feed status, language, theme, user),
// the offline banner and the sign-in gate. Hidden when printing.
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useTheme } from "next-themes";
import { api, roleAtLeast, setSession, type Role } from "@/lib/api";
import { useSession } from "@/lib/session";
import { useT } from "@/lib/i18n";
import { Icon } from "./Icon";

type NavKey = "overview" | "live" | "audit" | "plans" | "insights" | "copilot" | "reports" | "events" | "monthly" | "pilot" | "account" | "onboarding" | "connectors" | "admin";
const NAV: { key: NavKey; path: string; need?: Role }[] = [
  { key: "overview", path: "/" },
  { key: "live", path: "/live" },
  { key: "audit", path: "/audit" },
  { key: "plans", path: "/plans" },
  { key: "insights", path: "/insights" },
  { key: "copilot", path: "/copilot" },
  { key: "reports", path: "/reports" },
  { key: "events", path: "/events" },
  { key: "monthly", path: "/monthly" },
  { key: "pilot", path: "/pilot" },
  { key: "account", path: "/account" },
  { key: "onboarding", path: "/onboarding", need: "Admin" },
  { key: "connectors", path: "/connectors", need: "Admin" },
  { key: "admin", path: "/admin", need: "Admin" },
];

type Status = { api: boolean | null; feed: "live" | "waiting" | "down" | null };

/** API reachability + whether the simulator feed is publishing (polls /signals/latest). */
function useStatus(): Status {
  const [s, setS] = useState<Status>({ api: null, feed: null });
  useEffect(() => {
    let alive = true;
    const check = async () => {
      try {
        const r = await api<{ status: { received: number; newest: string | null } }>("/signals/latest?junction=J05");
        const age = r.status.newest ? (Date.now() - Date.parse(r.status.newest)) / 1000 : Infinity;
        if (alive) setS({ api: true, feed: age < 10 ? "live" : r.status.received ? "down" : "waiting" });
      } catch {
        if (alive) setS({ api: false, feed: null });
      }
    };
    check();
    const id = setInterval(check, 8000);
    // one failed request (e.g. a slow copilot answer) is not proof the API is down: re-check first
    const onApi = (e: Event) => {
      if (!(e as CustomEvent<boolean>).detail) check();
    };
    window.addEventListener("hb-api", onApi);
    return () => {
      alive = false;
      clearInterval(id);
      window.removeEventListener("hb-api", onApi);
    };
  }, []);
  return s;
}

function Dot({ on, warn }: { on: boolean | null; warn?: boolean }) {
  const c = on === null ? "var(--ink-3)" : on ? (warn ? "#ffb020" : "#22c55e") : "#ff3b30";
  return <span aria-hidden className={`inline-block size-2 rounded-full ${on && !warn ? "live-dot" : ""}`} style={{ background: c }} />;
}

export function Shell({ children }: { children: ReactNode }) {
  const { t, locale, href } = useT();
  const pathname = usePathname();
  const router = useRouter();
  const { session, ready } = useSession();
  const { resolvedTheme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const status = useStatus();
  useEffect(() => setMounted(true), []);
  useEffect(() => setOpen(false), [pathname]);

  // sign-in gate: every screen needs an officer session
  useEffect(() => {
    if (ready && !session) router.replace(`${href("/login")}?next=${encodeURIComponent(pathname)}`);
  }, [ready, session, router, href, pathname]);

  const rest = pathname.replace(/^\/(en|hi)/, "") || "/";
  const other = locale === "en" ? "hi" : "en";
  const active = (p: string) => (p === "/" ? rest === "/" : rest === p || rest.startsWith(`${p}/`)) || (p === "/" && rest.startsWith("/junction"));

  if (!ready || !session) return <div className="min-h-dvh" />;

  const nav = (
    <nav aria-label={t.nav.menu} className="flex flex-col gap-0.5">
      {NAV.filter((n) => !n.need || roleAtLeast(session.role, n.need)).map((n) => (
        <Link key={n.key} href={href(n.path)} aria-current={active(n.path) ? "page" : undefined}
          className="tab flex items-center gap-2.5 !py-2 hover:bg-[var(--accent-soft)]">
          <Icon name={n.key} />
          {t.nav[n.key]}
        </Link>
      ))}
    </nav>
  );

  return (
    <div className="app-frame min-h-dvh md:grid md:grid-cols-[236px_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 btn">{t.app.skip}</a>
      {/* sidebar (desktop) */}
      <aside className="no-print sticky top-0 hidden h-dvh flex-col gap-6 border-r border-[var(--line)] bg-[var(--panel)] px-3 py-5 md:flex">
        <Brand />
        {nav}
        <p className="faint mt-auto px-2 text-[11px] leading-snug">{t.app.readOnly}</p>
      </aside>

      <div className="min-w-0">
        <header className="no-print sticky top-0 z-30 flex items-center gap-2 border-b border-[var(--line)] bg-[var(--bg)]/85 px-3 py-2.5 backdrop-blur md:px-6">
          <button type="button" className="btn md:hidden !px-2.5" aria-label={t.nav.menu} aria-expanded={open} onClick={() => setOpen(true)}>
            <Icon name="menu" />
          </button>
          <div className="md:hidden"><Brand compact /></div>
          <div className="ml-auto flex items-center gap-1.5 md:gap-2">
            <span className="panel-2 hidden items-center gap-2 px-2.5 py-1.5 text-xs sm:inline-flex" title={`${t.top.api} ${status.api ? t.top.online : t.top.offline}`}>
              <Dot on={status.api} /> {t.top.api}
              <span className="faint">·</span>
              <Dot on={status.feed === null ? null : status.feed !== "down"} warn={status.feed === "waiting"} />
              {t.top.feed}: {status.feed === "live" ? t.top.feedLive : status.feed === "waiting" ? t.top.feedWaiting : status.feed === "down" ? t.top.feedDown : "—"}
            </span>
            <Link className="btn !px-2.5" href={`/${other}${rest === "/" ? "" : rest}`} hrefLang={other} aria-label={t.top.languageLabel} lang={other}>
              {t.top.language}
            </Link>
            <button type="button" className="btn !px-2.5" aria-label={t.top.theme} onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}>
              {mounted && <Icon name={resolvedTheme === "dark" ? "sun" : "moon"} />}
              {!mounted && <span className="size-[18px]" />}
            </button>
            <span className="hidden flex-col items-end text-right text-xs leading-tight lg:flex">
              <span className="font-semibold">{session.email}</span>
              <span className="faint">{t.role[session.role]}</span>
            </span>
            <button type="button" className="btn !px-2.5" aria-label={t.top.signOut} title={t.top.signOut} onClick={() => { api("/auth/logout", { method: "POST" }).catch(() => undefined).finally(() => setSession(null)); }}>
              <Icon name="out" />
            </button>
          </div>
        </header>

        {status.api === false && <OfflineBanner />}

        <main id="main" className="mx-auto w-full max-w-[1400px] px-4 py-6 md:px-8 md:py-8">
          {children}
        </main>
      </div>

      {/* mobile drawer */}
      {open && (
        <div className="no-print fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" aria-label={t.nav.menu}>
          <button type="button" aria-label={t.nav.close} className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 flex w-[80%] max-w-[300px] flex-col gap-5 overflow-y-auto bg-[var(--panel)] px-3 py-4">
            <div className="flex items-center justify-between">
              <Brand />
              <button type="button" className="btn !px-2.5" aria-label={t.nav.close} onClick={() => setOpen(false)}>
                <Icon name="close" />
              </button>
            </div>
            {nav}
            <p className="faint mt-auto px-2 text-[11px]">{t.app.readOnly}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  const { t, href } = useT();
  return (
    <Link href={href("/")} className="flex items-center gap-2.5 px-2">
      {/* three-aspect signal head with the green lit: the product in one glyph */}
      <span aria-hidden className="flex h-8 w-4 flex-col items-center justify-between rounded-[5px] bg-[var(--panel-2)] py-1 ring-1 ring-[var(--line)]">
        <span className="size-1.5 rounded-full bg-[#ff3b30]/25" />
        <span className="size-1.5 rounded-full bg-[#ffb020]/25" />
        <span className="size-1.5 rounded-full bg-[#22c55e] shadow-[0_0_6px_#22c55e]" />
      </span>
      <span className="flex flex-col leading-tight">
        <span className="text-[0.95rem] font-semibold">{t.app.name}</span>
        {!compact && <span className="faint text-[11px]">{t.app.tagline}</span>}
      </span>
    </Link>
  );
}

function OfflineBanner() {
  const { t } = useT();
  return (
    <div role="alert" className="no-print border-b border-[#ff3b30]/30 bg-[#ff3b30]/10 px-4 py-3 text-sm md:px-8">
      <p className="font-semibold">{t.offline.title}</p>
      <p className="muted mt-0.5">{t.offline.body}</p>
      <button type="button" className="btn mt-2 !min-h-8 !py-1" onClick={() => location.reload()}>
        {t.offline.retry}
      </button>
    </div>
  );
}
