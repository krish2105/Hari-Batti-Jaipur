// Next.js config. transpilePackages lets Next compile our shared TypeScript workspace packages.
// Security headers (P8 W16, OWASP ASVS 14.4) in production builds only (the dev server needs eval).
// connect-src allows the API origin (REST + WebSocket) and the map tiles; nothing else.
import type { NextConfig } from "next";
import path from "node:path";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const WS = API.replace(/^http/, "ws");
const TILES = "https://tiles.openfreemap.org";
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  `img-src 'self' data: blob: ${TILES}`,
  "font-src 'self' data:",
  `connect-src 'self' data: blob: ${API} ${WS} ${TILES}`,
  "worker-src 'self' blob:",
  "child-src 'self' blob:",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const nextConfig: NextConfig = {
  transpilePackages: ["@haribatti/core", "@haribatti/ui"],
  // The monorepo root holds the lockfile, so trace files from there.
  outputFileTracingRoot: path.join(__dirname, "../.."),
  poweredByHeader: false,
  async headers() {
    if (process.env.NODE_ENV !== "production") return [];
    const headers = [
      { key: "Content-Security-Policy", value: CSP },
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Referrer-Policy", value: "no-referrer" },
      { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
      { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
    ];
    if (API.startsWith("https://")) headers.push({ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" });
    return [{ source: "/:path*", headers }];
  },
};

export default nextConfig;
