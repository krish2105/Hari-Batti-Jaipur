// sitemap.xml for both languages.
import type { MetadataRoute } from "next";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "https://hari-batti-jaipur.vercel.app";

export default function sitemap(): MetadataRoute.Sitemap {
  return ["en", "hi"].map((l) => ({ url: `${SITE}/${l}`, changeFrequency: "monthly", priority: l === "en" ? 1 : 0.9 }));
}
