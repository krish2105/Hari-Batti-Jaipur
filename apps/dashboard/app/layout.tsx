// Root layout: fonts, theme provider and <html lang> (from the locale header set in middleware.ts).
import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { headers } from "next/headers";
import { Doto, IBM_Plex_Mono, Inter, Noto_Sans_Devanagari } from "next/font/google";
import { Providers } from "@/components/Providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], variable: "--font-mono", weight: ["400", "600"], display: "swap" });
const devanagari = Noto_Sans_Devanagari({ subsets: ["devanagari"], variable: "--font-devanagari", weight: ["400", "600", "700"], display: "swap", preload: false });
const doto = Doto({ subsets: ["latin"], variable: "--font-doto", weight: ["900"], display: "swap" });

export const metadata: Metadata = {
  title: { default: "Signal Command · HariBatti", template: "%s · Signal Command" },
  description: "Read-only signal audit and planning dashboard for the Mansarovar corridor, Jaipur.",
  robots: { index: false, follow: false }, // internal police tool
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = {
  themeColor: [{ media: "(prefers-color-scheme: dark)", color: "#0a1220" }, { media: "(prefers-color-scheme: light)", color: "#eef1f5" }],
  width: "device-width",
  initialScale: 1,
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const lang = (await headers()).get("x-hb-locale") === "hi" ? "hi" : "en";
  return (
    <html lang={lang} suppressHydrationWarning className={`${inter.variable} ${mono.variable} ${devanagari.variable} ${doto.variable}`}>
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
