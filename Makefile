# HariBatti — local commands. Run `make <target>` from the repo root.
# Reads .env if it exists (ports, URLs). See .env.example.
-include .env
export

OLLAMA_URL ?= http://localhost:11434
OLLAMA_MODEL ?= qwen2.5:7b
PY_PROJECTS := services/api services/sim services/ml

.PHONY: infra infra-down sim sim-build sim-calibrate sim-coords api test-py ollama-check demo

## Start Postgres/PostGIS (host port 5433) + Redis (host port 6380) and wait until healthy.
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

## Look up CANDIDATE coordinates on OpenStreetMap -> data/junction_coords_candidates.csv.
## Never edits data/junction_registry.csv: check each on Google Maps and copy them yourself.
sim-coords:
	cd services/sim && uv run python -m sim coords

## Run the FastAPI backend on http://localhost:8000 (docs at /docs).
api:
	cd services/api && uv run uvicorn app.main:app --reload --port 8000

## Run every Python test: each uv service + the data checks in scripts/tests.
test-py:
	@set -e; for p in $(PY_PROJECTS); do \
		echo "==> pytest $$p"; (cd $$p && uv run pytest -q); \
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

## One command demo: infra, then simulator (always from the 18:15 PM peak unless START= is given)
## + API + website side by side (Ctrl+C stops all).
demo: infra
	pnpm exec concurrently -n sim,api,web -c yellow,cyan,green \
		"$(MAKE) sim START=$(or $(START),18:15)" "$(MAKE) api" "pnpm dev:web"
