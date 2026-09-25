# HariBatti — Jaipur signal countdown + audit platform
Pilot: Mansarovar corridor, junctions J01–J08 (Mansarovar Metro ↔ Sanganer Stadium).

Read docs/00-master.md first, then the doc for the app you are working on:
- apps/web → docs/01-website.md
- apps/dashboard, services/* → docs/02-dashboard.md
- apps/mobile → docs/03-mobile.md
- traffic data findings → docs/05-data-analysis.md; data dictionary → data/README.md

## Hard rules
- ZERO paid APIs. The dashboard AI Copilot uses local Ollama (qwen2.5:7b at http://localhost:11434).
- The system NEVER controls a traffic signal. Read-only everywhere.
- Every number/timer shows its source: SIM, FIELD, SURVEY, CROWD or ITMS.
- App advice never says "go"; cap at speed limit minus 5 km/h.
- Work one phase at a time. Stop after each phase and wait for me.
- Simple-English comments on every file and non-obvious function.
- Before saying done: run lint + tests + build and fix all failures.
- Never commit secrets; use .env files (gitignored) and keep .env.example updated.

## Data (source of truth)
- Junction IDs J01–J08 come from data/junction_registry.csv. Never rename or invent junctions.
- Traffic volumes come ONLY from data/processed/*.csv (built from the May 2026 survey by
  scripts/process_tmc.py). Never invent or "sample" counts. Label them "Survey, May 2026".
- Signal timings come from data/signal_timings.csv; if a junction is missing, use a default
  plan and label it "Assumed timing".
- data/raw/tmc is CONFIDENTIAL survey data: never copy raw sheets into apps/web or any public
  output; show only aggregates.

## Commands
- JS: pnpm workspaces. Python: uv (Python 3.12).
- Local infra: `make infra` (Postgres/PostGIS + Redis via Docker/OrbStack).
- Dev: `make sim`, `make api`, `pnpm dev:web`, `pnpm dev:dashboard`, `pnpm dev:mobile`.
