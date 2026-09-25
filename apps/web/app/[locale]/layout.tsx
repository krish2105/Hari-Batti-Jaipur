// Root layout per locale (/en, /hi): fonts, theme, <html lang>, metadata.
import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { Doto, Fraunces, Inter, Noto_Sans_Devanagari } from "next/font/google";
import { Providers } from "@/components/ui/Providers";
import { getMessages, isLocale, locales } from "@/lib/i18n";
import "../globals.css";

const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces", axes: ["SOFT", "WONK", "opsz"], display: "swap" });
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const devanagari = Noto_Sans_Devanagari({ subsets: ["devanagari"], variable: "--font-devanagari", weight: ["400", "500", "700"], display: "swap" });
const doto = Doto({ subsets: ["latin"], variable: "--font-doto", weight: ["700", "900"], display: "swap" });

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "https://hari-batti-jaipur.vercel.app";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) return {};
  const m = getMessages(locale).meta;
  return {
    metadataBase: new URL(SITE),
    title: m.title,
    description: m.description,
    alternates: { canonical: `/${locale}`, languages: { en: "/en", hi: "/hi" } },
    openGraph: { title: m.title, description: m.description, type: "website", locale: locale === "hi" ? "hi_IN" : "en_IN", url: `/${locale}` },
    twitter: { card: "summary_large_image", title: m.title, description: m.description },
    icons: { icon: "/icon.svg" },
  };
}

export const viewport: Viewport = {
  themeColor: [{ media: "(prefers-color-scheme: dark)", color: "#0f1b2d" }, { media: "(prefers-color-scheme: light)", color: "#f7e4dd" }],
  width: "device-width",
  initialScale: 1,
};

export default async function LocaleLayout({ children, params }: { children: ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return (
    <html lang={locale} suppressHydrationWarning className={`${fraunces.variable} ${inter.variable} ${devanagari.variable} ${doto.variable}`}>
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
