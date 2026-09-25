// Tiny i18n: every visible string lives in messages/en.json and messages/hi.json.
import en from "@/messages/en.json";
import hi from "@/messages/hi.json";

export const locales = ["en", "hi"] as const;
export type Locale = (typeof locales)[number];
export type Messages = typeof en;

const all: Record<Locale, Messages> = { en, hi: hi as Messages };

export function isLocale(x: string): x is Locale {
  return (locales as readonly string[]).includes(x);
}

export function getMessages(locale: Locale): Messages {
  return all[locale];
}

/** Replace {name} placeholders. */
export function fmt(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? `{${k}}`));
}

/** Numbers in the Indian system (12,34,567) for both languages; digits stay Latin for legibility. */
export function num(n: number, digits = 0): string {
  return n.toLocaleString("en-IN", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}
