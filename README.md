# HariBatti — Starter Kit (START HERE)

Jaipur traffic-signal countdown app + police audit dashboard + 3D website.

## What's inside

| Path | What it is | Do you attach it? |
| --- | --- | --- |
| `CLAUDE.md` | Project rules; Claude Code reads it automatically every session | No — auto-loaded |
| `docs/00-master.md` | Master plan, pilot, architecture | No — referenced by prompts |
| `docs/01-website.md` | 3D website spec | No |
| `docs/02-dashboard.md` | Police dashboard + backend spec | No |
| `docs/03-mobile.md` | iOS/Android app spec | No |
| `docs/04-runbook.md` | Every terminal command, in order | You read it |
| `docs/05-data-analysis.md` | Findings from your May 2026 traffic counts | No — referenced |
| `data/` | Survey data (raw + processed) + registry + timing template | No — read from disk |
| `scripts/process_tmc.py` | Rebuilds `data/processed/` from the raw survey files | You run it once |
| `prompts/*.md` | One prompt per build phase, with launch command | You paste the text |
| `scripts/setup-mac.sh` | One-time Mac setup | You run it |

Claude Code reads files straight from this folder, so nothing needs attaching. To point at a file explicitly, type `@docs/02-dashboard.md` in your prompt.

**Data already inside (from your uploads)**
- `data/raw/tmc/` — the 20 original survey workbooks (24-h turning counts, 11–12 May 2026)
- `data/processed/` — clean CSVs made by `scripts/process_tmc.py` (Claude Code reads these)
- `data/junction_registry.csv` — the 8 pilot junctions J01–J08 (fill lat/lng + lanes)
- `docs/05-data-analysis.md` — what the counts show

**Things you still add later** (drop in the folder; Claude Code reads them)
- `data/signal_timings.csv` — your stopwatch timings (template provided)
- `data/cad/*.dwg` + `.dxf` — the road drawing, if you have it
- Screenshots of design references or bugs → paste with Ctrl+V into Claude Code

## 3 steps to start

```bash
unzip ~/Downloads/hari-batti-starter.zip -d ~/Projects && cd ~/Projects/hari-batti
bash scripts/setup-mac.sh          # one time, then open a new Terminal
cat docs/04-runbook.md             # follow section 3 onward
```

## Local ports

| Service | Port |
| --- | --- |
| Postgres + PostGIS (Docker) | 5434 (Homebrew Postgres keeps 5432 and 5433) |
| Redis (Docker) | 6380 (Homebrew Redis keeps 6379) |
| API | 8000 |
| Website / Dashboard | 3000 / 3001 |
| Ollama | 11434 |

Set in `.env` (copy `.env.example`). Full details: `docs/04-runbook.md` section 4b.
