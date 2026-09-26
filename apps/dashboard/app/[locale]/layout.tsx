// Locale segment (/en, /hi): validates the locale and provides the strings to every page.
import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { I18nProvider } from "@/lib/i18n";
import { isLocale } from "@/lib/locales";

export function generateStaticParams() {
  return [{ locale: "en" }, { locale: "hi" }];
}

export default async function LocaleLayout({ children, params }: { children: ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return <I18nProvider locale={locale}>{children}</I18nProvider>;
}
