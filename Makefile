# HariBatti — local commands. Run `make <target>` from the repo root.
# Reads .env if it exists (ports, URLs). See .env.example.
-include .env
export

OLLAMA_URL ?= http://localhost:11434
OLLAMA_MODEL ?= qwen2.5:7b
PY_PROJECTS := services/api services/sim services/ml services/cv

.PHONY: field-study sim-calibrate-day infra infra-down sim sim-build sim-calibrate sim-coords api test-py ollama-check demo e2e-dashboard cv-fetch cv-eval cv-video cv-frame opt-train opt-eval forecast

## Start Postgres/PostGIS (host port 5434) + Redis (host port 6380) and wait until healthy.
infra:
	docker compose up -d --wait

## Stop the local infra (data volumes are kept).
infra-down:
	docker compose down

## Run the live simulator: PhaseState JSON at 1 Hz to Redis channel "signals" (host port 6380).
## Starts at the current India time (Asia/Kolkata); override with START=HH:MM, PLAN=even|webster4.
sim:
	cd services/sim && uv run python -m sim run $(if $(START),--start $(START)) $(if $(PLAN),--plan $(PLAN))

## Build network + signal plans + survey demand (cached; OSM automatically once registry has coords).
sim-build:
	cd services/sim && uv run python -m sim build

## One command to re-run everything: build, then the GEH calibration/validation report
## (services/sim/reports/calibration.md). Full day by default; HOURS=3 for a quick partial run.
sim-calibrate:
	cd services/sim && uv run python -m sim calibrate $(if $(HOURS),--hours $(HOURS))

## W1 full-day calibration in 3-hour windows (about 1.5 h) -> services/sim/reports/calibration.md.
sim-calibrate-day:
	cd services/sim && uv run python -m sim.calibrate_windows

## Look up CANDIDATE coordinates on OpenStreetMap -> data/junction_coords_candidates.csv.
## Never edits data/junction_registry.csv: check each on Google Maps and copy them yourself.
sim-coords:
	cd services/sim && uv run python -m sim coords

## Run the FastAPI backend on http://localhost:8000 (docs at /docs). First migrates + seeds Postgres
## and computes the hourly Health metrics (skipped with a warning if `make infra` is not running).
# --timeout-graceful-shutdown: open dashboard WebSockets (live wall) would otherwise block Ctrl-C / restarts forever.
api:
	cd services/api && uv run python -m app.bootstrap && uv run uvicorn app.main:app --reload --port 8000 --timeout-graceful-shutdown 3

## Run every Python test: each uv service + the data checks in scripts/tests.
## PYTEST_ARGS='-m "not sumo"' skips the slow SUMO tests (used by CI).
test-py:
	@set -e; for p in $(PY_PROJECTS); do \
		echo "==> pytest $$p"; (cd $$p && uv run pytest -q $(PYTEST_ARGS)); \
	done
	@echo "==> pytest scripts/tests (data checks)"
	uv run --no-project --python 3.12 --with pytest pytest -q scripts/tests

## Check local Ollama is running and has the Copilot model (free, no paid APIs).
ollama-check:
	@tags=$$(curl -sf --max-time 5 $(OLLAMA_URL)/api/tags) \
		|| { echo "Ollama is not answering at $(OLLAMA_URL). Fix: brew services restart ollama"; exit 1; }; \
	echo "$$tags" | grep -q '"name":"$(OLLAMA_MODEL)"' \
		|| { echo "Ollama is up but $(OLLAMA_MODEL) is missing. Fix: ollama pull $(OLLAMA_MODEL)"; exit 1; }; \
	echo "OK: Ollama is up at $(OLLAMA_URL) with $(OLLAMA_MODEL)"

## One command, fully offline demo: infra, then the simulator (from the 18:15 PM peak unless START=
## is given) + API + Signal Command dashboard + website side by side (Ctrl+C stops all).
## Sign in at http://localhost:3001 with DEMO_EMAIL; the login screen shows the one-time code
## because no email service runs on a laptop (AUTH_DEV_ECHO_OTP, development only).
DEMO_EMAIL ?= admin@haribatti.local
demo: infra
	pnpm exec concurrently -n sim,api,dash,web -c yellow,cyan,magenta,green \
		"$(MAKE) sim START=$(or $(START),18:15)" \
		"$(MAKE) api AUTH_DEV_ECHO_OTP=true ADMIN_EMAILS=$(or $(ADMIN_EMAILS),$(DEMO_EMAIL))" \
		"pnpm dev:dashboard" "pnpm dev:web"

## Dashboard smoke tests (Playwright, every screen in en + hi at desktop and 375 px widths).
## Needs `make demo` (or `make api` + `pnpm dev:dashboard`) running in another tab.
e2e-dashboard:
	HB_API_URL=$(or $(HB_API_URL),http://localhost:8000) E2E_EMAIL=$(DEMO_EMAIL) \
		pnpm --filter dashboard exec playwright test

## Computer vision (W4). Download the RT-DETR code, the Apache-2.0 weights and a UVH-26 sample (< 2 GB).
cv-fetch:
	cd services/cv && uv run --group model python -m hbcv.fetch

## mAP of the IISc UVH-26 model vs the COCO baseline on the sample -> services/cv/reports/cv_eval.json
cv-eval:
	cd services/cv && uv run --group model python -m hbcv.evaluate && uv run python -m hbcv.report

## Save the first frame of a video so you can draw the camera profile (zones, stop line, lamp ROI).
cv-frame:
	cd services/cv && uv run --group model python -m hbcv.intake probe "$(abspath $(VIDEO))" out/first_frame  # privacy-blurred frame

## Counts, queues, saturation flow, signal state and a blurred preview from a junction video:
##   make cv-video VIDEO=clip.mp4 JUNCTION=J05   (needs services/cv/profiles/J05.json; see TEMPLATE.json)
cv-video:
	cd services/cv && uv run --group model python -m hbcv.video "$(abspath $(VIDEO))" $(JUNCTION)

## Signal-timing optimisation (W2, SIM): train PPO agents, then compare every controller on 12 May.
opt-train:
	cd services/sim && uv run --group rl python -m sim.opt.train single --seed 0 && uv run --group rl python -m sim.opt.train corridor --seed 0

opt-eval:
	cd services/sim && uv run --group rl python -m sim.opt.evaluate && uv run python -m sim.opt.report

## Forecasting and anomaly detection (W5) -> services/ml/reports/forecasting.md
forecast:
	cd services/ml && uv run --group forecast python -m ml.w5.run

## Field study (W14): analyse the 20 GPS test drives. Without EXPORT it runs on 20 synthetic (SIM) runs.
## Real runs: download GET /study/export (Admin) to a file outside the repo, then make field-study EXPORT=path
field-study:
	cd services/ml && uv run python -m ml.study $(if $(EXPORT),--export $(EXPORT),--synthetic)
