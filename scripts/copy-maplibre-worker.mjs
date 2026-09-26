// Copy MapLibre GL's web-worker files into each app's public/ folder (P8 W16).
// MapLibre 6 finds its worker next to its own module file, which a Next.js bundle cannot provide, so
// the apps call setWorkerUrl("/vendor/maplibre/maplibre-gl-worker.mjs"). Run after upgrading
// maplibre-gl:  node scripts/copy-maplibre-worker.mjs   (a test checks the copies match the package)
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
for (const app of ["web", "dashboard"]) {
  const src = join(root, "apps", app, "node_modules", "maplibre-gl", "dist");
  const out = join(root, "apps", app, "public", "vendor", "maplibre");
  mkdirSync(out, { recursive: true });
  for (const f of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) copyFileSync(join(src, f), join(out, f));
  const { version } = JSON.parse(readFileSync(join(src, "..", "package.json"), "utf8"));
  writeFileSync(join(out, "VERSION"), `${version}\n`);
  console.log(`[maplibre] ${app}: worker ${version} -> public/vendor/maplibre/`);
}
