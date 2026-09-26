"use client";
// Tiny i18n: every visible string lives in messages/en.json and messages/hi.json (same keys).
// Pages read strings with useT(); the locale comes from the URL (/en/..., /hi/...).
import { createContext, useContext, type ReactNode } from "react";
import en from "@/messages/en.json";
import hi from "@/messages/hi.json";
import type { Locale } from "./locales";

export type { Locale } from "./locales";
export type Messages = typeof en;

const all: Record<Locale, Messages> = { en, hi: hi as Messages };

const Ctx = createContext<{ locale: Locale; t: Messages }>({ locale: "en", t: en });

export function I18nProvider({ locale, children }: { locale: Locale; children: ReactNode }) {
  return <Ctx.Provider value={{ locale, t: all[locale] }}>{children}</Ctx.Provider>;
}

/** { t, locale, href } — href("/audit") gives "/hi/audit" on Hindi pages. */
export function useT() {
  const { locale, t } = useContext(Ctx);
  return { t, locale, href: (path: string) => `/${locale}${path === "/" ? "" : path}` };
}

/** Replace {name} placeholders. */
export function fmt(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? `{${k}}`));
}

/** Numbers in the Indian system (12,34,567); digits stay Latin in both languages for legibility. */
export function num(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export const messages = all;
