# services/sim — Mansarovar corridor digital twin (SUMO)

Replays the May 2026 survey counts (J01–J08) in SUMO and publishes one PhaseState JSON per
approach per second to Redis channel `signals` (8 junctions × 4 approaches = 32 messages/s).
Read-only: it never talks to a real signal.

| Command | What it does |
| --- | --- |
| `make sim` | Live stream from the current **India** time (Asia/Kolkata). `START=18:15`, `PLAN=even\|webster4` |
| `make demo` | Infra + sim (from 18:15) + API + website |
| `make sim-build` | Build network, signal plans and 24-h demand (cached in `build/`, gitignored) |
| `make sim-calibrate` | Build + headless run + GEH report → `reports/calibration.md` (`HOURS=3` for a quick run) |
| `make sim-coords` | Candidate coordinates from OpenStreetMap → `data/junction_coords_candidates.csv` |

**Network.** Until every registry row has lat/lng the sim uses the *Schematic network – coordinates
pending* (straight rows, arm positions from the survey's own L/S/R turn labels, left-hand traffic).
With coordinates it downloads OpenStreetMap roads and uses them automatically.

**Timing.** Real rows in `data/signal_timings.csv` win. Otherwise one of three labelled plans:
`demand2` *Assumed timing – demand-proportional (2-phase, free left)* (default), `webster4`
(approach-wise Webster, oversaturated → 180 s) and `even` *Assumed timing – even split* (4 × 25 s).

**Demand.** Only `data/processed/tmc_clean.csv`. SUMO routeSampler fits routes to every junction's
15-min turning counts at once. Two-wheelers filter between cars (sublane model, 0.8 m).

**Assumptions** (lanes, spacing, saturation flow, timings, sublane) live in `assumptions.toml` and are
listed in every build manifest and report.

    uv run pytest -q     # unit tests (fast; uses a temp build without demand)
