// Vitest for the dashboard's pure logic (lib/). Resolves the "@/..." alias used by the app.
import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: { alias: { "@": path.resolve(__dirname) } },
  test: { include: ["test/**/*.test.ts"] },
});
