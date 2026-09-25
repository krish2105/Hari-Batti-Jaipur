// Next.js config. transpilePackages lets Next compile our shared TypeScript workspace packages.
import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  transpilePackages: ["@haribatti/core", "@haribatti/ui"],
  // The monorepo root holds the lockfile, so trace files from there.
  outputFileTracingRoot: path.join(__dirname, "../.."),
};

export default nextConfig;
