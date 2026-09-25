<!-- Launch: claude --model opus --effort high --permission-mode plan -->
Read CLAUDE.md and docs/00-master.md. Build the monorepo skeleton:
pnpm workspaces (apps/web, apps/dashboard, apps/mobile, packages/core, packages/ui),
uv Python projects (services/api, services/sim, services/ml),
docker-compose.yml (postgis/postgis:16 + redis:7),
packages/core with Junction/PhaseState types + glosa.ts adviseSpeed (copy from docs/03-mobile.md) + Vitest tests
(including the 300 m example = 30 km/h),
data/junctions.geojson generated from data/junction_registry.csv (J01–J08, Mansarovar corridor; coords blank until I fill them — use placeholders flagged "verify").
Load data/processed/*.csv as the source of truth for traffic volumes; never invent counts.
Create these exact commands:
- root package.json scripts: dev:web, dev:dashboard, dev:mobile, lint, test, build
- Makefile targets: infra, infra-down, sim, api, test-py, ollama-check, demo
Stop after this phase and tell me how to verify.
