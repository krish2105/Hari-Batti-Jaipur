// Shared ESLint config for plain TypeScript packages (packages/*, apps/mobile).
// The two Next.js apps have their own eslint.config.mjs that adds Next's rules.
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import globals from "globals";

export default tseslint.config(
  { ignores: ["**/dist/**", "**/.next/**", "**/.expo/**", "**/node_modules/**"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    languageOptions: { globals: { ...globals.node, ...globals.browser } },
  },
);
