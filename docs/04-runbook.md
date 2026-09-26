# HariBatti 04 — Terminal Runbook (macOS)

As of 26 Sep 2026 · Krishna Mathur. All commands are for Terminal (zsh) on Apple silicon.

## 1. Put the folder in place

```bash
mkdir -p ~/Projects
# unzip the downloaded starter kit into ~/Projects
unzip ~/Downloads/hari-batti-starter.zip -d ~/Projects
cd ~/Projects/hari-batti
ls            # CLAUDE.md  README.md  docs/  scripts/ ...  (build prompts: docs-private/prompts/, not in git)
```

## 2. One-time Mac setup (20–40 min)

```bash
bash scripts/setup-mac.sh
# then close Terminal and open a new window
```

Optional visual simulator: `brew install --cask xquartz && brew tap dlr-ts/sumo && brew install sumo` (log out/in after XQuartz).
Optional emulators: `brew install --cask android-studio`; Xcode from the App Store. Easiest: Expo Go app on your phone.

## 3. Claude Code login + git

```bash
cd ~/Projects/hari-batti
claude doctor                 # check install + login
claude                        # first run: log in in the browser, then /exit

git init -b main
git add -A && git commit -m "chore: specs and CLAUDE.md"
gh auth login                 # HTTPS + browser
gh repo create hari-batti --private --source=. --push
```

## 3b. Rebuild the processed traffic data (once, and after adding new survey files)

```bash
cd ~/Projects/hari-batti
uv run --with pandas --with openpyxl python scripts/process_tmc.py
# expect: OK: 16,128 rows, 8 junctions, 14 junction-days
```

## 4. Build loop (every phase)

1. Open the prompt file for the phase in `docs-private/prompts/` (local only, not in git); its first line shows the launch command.
2. Run that launch command in the repo folder.
3. Paste the prompt text (not the `<!-- -->` lines). Read the plan, press Shift+Tab to leave plan mode and approve.
4. When done, verify in a second Terminal tab (Cmd+T) with the commands below.
5. Commit, then `/clear` in Claude Code before the next phase.

```bash
git add -A && git commit -m "feat: <phase>" && git push
```

| Phase | Prompt file | Launch | Verify |
| --- | --- | --- | --- |
| P1 Scaffold | docs-private/prompts/P1-scaffold.md | `claude --model opus --effort high --permission-mode plan` | `pnpm install && pnpm lint && pnpm test && pnpm build && make infra && docker compose ps && make test-py` (Postgres on 5434, Redis on 6380) |
| P2 Simulator | docs-private/prompts/P2-simulator.md | same as P1 | `make infra` · Tab 1: `make sim` (or `START=18:15`) · Tab 2: `docker compose exec redis redis-cli SUBSCRIBE signals` · `make sim-calibrate` → services/sim/reports/calibration.md · `make sim-coords` |
| P3 API | docs-private/prompts/P3-api.md | same as P1 | `make api` then `curl -s localhost:8000/junctions \| jq '.[0]'` and `make test-py` |
| P4 Website (6 sub-phases) | docs-private/prompts/P4-website.md | `claude --model sonnet --effort high --permission-mode plan` | `pnpm dev:web` → http://localhost:3000 · `pnpm --filter web build` |
| P5a ML | docs-private/prompts/P5a-ml.md | same as P1 | `make test-py` |
| P5b Dashboard (Phases 4–6) | docs-private/prompts/P5b-dashboard.md | `claude --model sonnet --effort medium --permission-mode plan` | `make ollama-check && pnpm dev:dashboard` → http://localhost:3001 |
| P6 Mobile (Phases 1–5) | docs-private/prompts/P6-mobile.md | `claude --model sonnet --effort medium --permission-mode plan` | `ipconfig getifaddr en0` → put in apps/mobile/.env · `pnpm dev:mobile` · scan QR in Expo Go |
| Any error | docs-private/prompts/STUCK.md | `claude --model sonnet --effort low` | — |

Inside Claude Code: `/model`, `/effort`, Shift+Tab (plan mode), `/clear`, Ctrl+O (see reasoning), `/exit`.

## 4b. Local ports

Homebrew Postgres already uses 5432 and 5433, and Homebrew Redis 6379, on this Mac, so Docker uses other host ports.
Change them in `.env` (copy from `.env.example`) if needed.

| Service | URL / port | Notes |
| --- | --- | --- |
| Postgres + PostGIS (Docker) | `localhost:5434` | `postgresql://haribatti:<password>@localhost:5434/haribatti` |
| Redis (Docker) | `localhost:6380` | `redis://localhost:6380/0`, channel `signals` |
| API | http://localhost:8000 | docs at /docs, health at /health |
| Website | http://localhost:3000 | `pnpm dev:web` |
| Dashboard | http://localhost:3001 | `pnpm dev:dashboard` |
| Ollama | http://localhost:11434 | model `qwen2.5:7b` |

Inside Docker the containers still use 5432/6379, so `docker compose exec redis redis-cli ...` and
`docker compose exec postgres psql -U haribatti` work without a port flag. From the Mac use
`redis-cli -p 6380` and `psql -h localhost -p 5434 -U haribatti`. The PostGIS image is amd64-only
and runs under Rosetta in OrbStack.

## 5. Daily run (5 tabs)

| Tab | Command |
| --- | --- |
| 1 | `make infra` (Postgres 5434, Redis 6380) |
| 2 | `make sim` |
| 3 | `make api` (docs at http://localhost:8000/docs) |
| 4 | `pnpm dev:web` or `pnpm dev:dashboard` |
| 5 | `pnpm dev:mobile` |

Or one command after P1: `make demo`. End of day: `pnpm lint && pnpm test && make test-py && git add -A && git commit -m "wip" && git push && make infra-down`.

## 6. Deploy

```bash
# Website (or: vercel.com → import repo → Root Directory apps/web)
vercel login && vercel link && vercel --prod

# Android test APK (share link with testers)
cd apps/mobile && eas login && eas build:configure && eas build -p android --profile preview

# Later: store releases
eas build -p android --profile production && eas submit -p android   # $25 Play account
eas build -p ios --profile production && eas submit -p ios           # $99/yr Apple account
```

Dashboard + API stay on your laptop until the police MoU.

## 7. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `command not found: brew` | `eval "$(/opt/homebrew/bin/brew shellenv)"`, reopen Terminal |
| `command not found: claude` | `source ~/.zshrc`, then `claude doctor` |
| Docker daemon not running | `open -a OrbStack`, wait 10 s |
| Port in use | `lsof -ti :3000 \| xargs kill -9` |
| `SUMO_HOME not set` | `export SUMO_HOME="$(cd services/sim && uv run python -c 'import sumo; print(sumo.SUMO_HOME)')"` |
| Ollama silent | `brew services restart ollama && ollama list` |
| Phone can't reach API | Same Wi-Fi; LAN IP in apps/mobile/.env; allow Python in macOS firewall |
| Expo QR fails | `pnpm dev:mobile -- --tunnel` |
| Claude Code off-plan | Esc, `/clear`, re-paste the phase prompt |
| Usage limit | `/model sonnet` + `/effort low` for small fixes; big phases later |
| Reset local data | `docker compose down -v && make infra` |
