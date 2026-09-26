// Vitest for the app's pure logic (src/lib, src/i18n). React Native screens are not tested here.
import { defineConfig } from "vitest/config";

export default defineConfig({ test: { include: ["test/**/*.test.ts"] } });
