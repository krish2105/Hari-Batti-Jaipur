// sitemap.xml for both languages.
import type { MetadataRoute } from "next";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "https://hari-batti-jaipur.vercel.app";

const PAGES = ["", "/pricing", "/security", "/status", "/contact"];

export default function sitemap(): MetadataRoute.Sitemap {
  return ["en", "hi"].flatMap((l) =>
    PAGES.map((p) => ({ url: `${SITE}/${l}${p}`, changeFrequency: "monthly" as const, priority: p ? 0.6 : l === "en" ? 1 : 0.9 })),
  );
}
