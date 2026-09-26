// Next.js config. transpilePackages lets Next compile our shared TypeScript workspace packages.
// Security headers (P8 W16, OWASP ASVS 14.4) are sent in production builds only: the dev server
// needs eval for fast refresh. The CSP lists every outside origin the site uses (map tiles only).
import type { NextConfig } from "next";
import path from "node:path";

const TILES = "https://tiles.openfreemap.org";
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'", // Next inline bootstrap; Draco decoder is WebAssembly
  "style-src 'self' 'unsafe-inline'",
  `img-src 'self' data: blob: ${TILES}`,
  "font-src 'self' data:",
  `connect-src 'self' data: blob: ${TILES}`, // GLTF textures and map sprites are decoded from blobs
  "worker-src 'self' blob:", // MapLibre and Draco run in blob workers
  "child-src 'self' blob:",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "upgrade-insecure-requests",
].join("; ");

export const SECURITY_HEADERS = [
  { key: "Content-Security-Policy", value: CSP },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
];

const nextConfig: NextConfig = {
  transpilePackages: ["@haribatti/core", "@haribatti/ui", "three"],
  // The monorepo root holds the lockfile, so trace files from there.
  outputFileTracingRoot: path.join(__dirname, "../.."),
  poweredByHeader: false,
  images: { formats: ["image/avif", "image/webp"] },
  async headers() {
    return process.env.NODE_ENV === "production" ? [{ source: "/:path*", headers: SECURITY_HEADERS }] : [];
  },
};

export default nextConfig;
