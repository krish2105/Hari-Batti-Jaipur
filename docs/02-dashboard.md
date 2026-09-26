# HariBatti 02 — Signal Command Dashboard (Police)

As of 26 Sep 2026 · Krishna Mathur

## Purpose and users

Signal Command is a read-only audit and planning dashboard: it shows where signals waste time or treat an approach unfairly, and recommends better timing plans. It never controls a signal. A human officer approves every change in the real ITMS.

| User | Main question | Screen |
| --- | --- | --- |
| Traffic DCP | "Is the Mansarovar corridor improving, and what do I tell the press?" | Corridor overview + monthly report |
| Abhay Command Centre operator | "Which junction needs attention right now?" | Live wall + alerts |
| Traffic inspector (field) | "What's wrong at my junction?" | Junction detail on mobile browser |
| Traffic engineer | "What timing plan should this fixed junction use?" | Plan Studio (simulation) |

Login: email + OTP, three roles (Viewer, Operator, Admin). Pilot data only for the 8 Mansarovar junctions (J01–J08).

## Screens and features

Seven screens. Build 1–4 for the police demo; 5–7 make it a product.

| # | Screen | What it shows | Key features |
| --- | --- | --- | --- |
| 1 | Corridor overview | Mansarovar corridor map, 8 junctions coloured by Health Score, corridor KPIs | Time filter (peak / off-peak / date range), source badge (Sim / Field / ITMS) |
| 2 | Live wall | Grid of 8 junction tiles with live phase + countdown | Alerts: spillback, signal dark, flashing amber in daytime, phase stuck |
| 3 | Junction detail | Per-approach red wait, green time, queue, cycles-to-clear, pedestrian clearance | Phase ring diagram, 24-hour heatmap, camera snapshot slot |
| 4 | Fairness audit | Every phase ranked by "starvation" and pedestrian compliance | One-click PDF: "Top 10 fixes this month" |
| 5 | Plan Studio | SUMO digital twin of the corridor | Try new cycle lengths, splits and offsets; compare before/after delay, stops, CO2 |
| 6 | AI Copilot | Chat box for officers | "Why was Rambagh slow on Tuesday 6 pm?" → answer with chart + data used |
| 7 | Citizen reports | Map of app reports (broken, hidden, bad timing) | AI-grouped duplicates, status: New / Assigned / Fixed |

**Special modes**

- **Event mode**: saved plans for SMS Stadium matches, Teej and Gangaur processions, VIP movement; shows diversions to push to the app.
- **Green corridor**: plan an ambulance route and see which junctions would need a green hold (recommendation only).
- **Monthly report**: auto-generated PDF with hours, fuel and CO2 saved, in English and Hindi.

## AI and analytics

Five metrics roll up into one 0–100 Junction Health Score. Weights are starting values to tune with field data.

| Metric | Definition | Bad when |
| --- | --- | --- |
| Average red wait (s) | Mean time a vehicle waits from arrival to green | Above 60 s |
| Cycles-to-clear | Signal cycles a queued vehicle needs to pass | Above 1.2 on average |
| Green starvation ratio | Green given ÷ green needed to clear the queue | Below 0.8 |
| Pedestrian clearance ratio | Pedestrian time ÷ (crossing width ÷ 1.0 m/s) | Below 1.0 |
| Spillback minutes | Minutes the queue reaches the upstream junction | Any |

```
Health = 100 - (30*s_wait + 25*s_clear + 20*s_starve + 15*s_ped + 10*s_spill)
```

Each s value is a 0–1 penalty scaled from its "bad when" threshold.

**Models**

| Model | Input | Output | Tool |
| --- | --- | --- | --- |
| Vehicle counter (services/cv) | Junction video (police CCTV or our own clip); the May 2026 survey counts cover the pilot | Turning counts by class, queue length, saturation flow, signal state | RT-DETRv2-S with IISc UVH-26 weights (Apache-2.0) + ByteTrack, faces and plates blurred first (Apple MPS). Ultralytics YOLO (AGPL) is not used |
| Phase predictor | Past phase logs + time of day + counts | Seconds until next change, with confidence | LSTM or gradient boosting; exact only with ITMS feed |
| Crowd phase estimator | Anonymous app GPS (stop and go events) | Estimated cycle and phase start times | Clustering over stop-release times |
| Plan optimiser | Demand counts per approach | Cycle length, splits, corridor offsets | Webster baseline, then SUMO + optimiser (OR-Tools or RL) |
| AI Copilot | Officer question | Answer + chart + SQL it ran | **Local Ollama (qwen2.5:7b)** with read-only SQL tools — no paid API |

**Webster baseline for fixed-timer junctions**

```
C0 = (1.5 * L + 5) / (1 - Y)
```

C0 is the optimal cycle length in seconds, L is total lost time per cycle, Y is the sum of critical flow ratios. Green time is split in proportion to each phase's flow ratio.

## Backend

FastAPI serves both the dashboard and the mobile app. A `PhaseSource` interface hides where signal data comes from, so the police feed plugs in later without touching the front-ends.

```python
# services/api/sources/base.py
class PhaseSource(Protocol):
    """Any provider of live signal phases (simulator, crowd, police ITMS)."""
    name: Literal["SIM", "CROWD", "ITMS"]
    async def stream(self) -> AsyncIterator[PhaseState]: ...   # 1 Hz updates
    async def history(self, junction_id: str, start: datetime, end: datetime) -> list[PhaseState]: ...
```

**Endpoints**

| Method | Path | Returns |
| --- | --- | --- |
| GET | `/junctions` | All pilot junctions with control type |
| GET | `/junctions/{id}/metrics?from&to` | Health score + 5 metrics |
| GET | `/corridor/mansarovar/kpis?from&to` | Corridor totals |
| WS | `/ws/signals` | Live PhaseState stream |
| POST | `/plans/simulate` | Runs SUMO with a proposed plan, returns before/after |
| POST | `/copilot/ask` | Local LLM answer + chart spec + SQL used |
| GET/POST | `/reports` | Citizen reports list / create (from app) |
| GET | `/reports/monthly.pdf?month` | Monthly PDF |

**Database (PostgreSQL + PostGIS)**

| Table | Key columns |
| --- | --- |
| `junctions` | id, name, geom, control_type |
| `approaches` | id, junction_id, bearing, crossing_width_m |
| `phase_events` | junction_id, approach_id, colour, start_ts, end_ts, source |
| `counts` | junction_id, survey_date, movement, from_approach, to_approach, turn, slot, class columns, total_veh, total_pcu (loaded from data/processed/tmc_clean.csv) |
| `metrics_hourly` | junction_id, hour, red_wait_s, cycles_to_clear, starvation, ped_ratio, spill_min, health |
| `citizen_reports` | id, geom, type, photo_url, status, created_at |
| `users` | id, email, role |

**Simulator (`services/sim`)**: install SUMO via `uv add eclipse-sumo traci sumolib`; build the Mansarovar corridor network from OSM with `netconvert`; build demand (routes + turn ratios per 15-min slot) from `data/processed/tmc_clean.csv`; run SUMO via TraCI; publish each signal's phase to Redis channel `signals` every second. The API's `SimSource` reads that channel.

## Build phases (for Claude Code)

- Phase 1 — Simulator: OSM extract for the Mansarovar corridor (J01–J08 in data/junction_registry.csv), netconvert, demand from data/processed/tmc_clean.csv (real 24-h counts, 15-min slots, turn ratios); signal timings from data/signal_timings.csv, else a clearly-flagged default plan, TraCI loop publishing PhaseState to Redis at 1 Hz.
- Phase 2 — API: PhaseSource, SimSource, all endpoints, Postgres schema + migrations, hourly metrics job with the five metrics and Health Score (unit-tested against hand-worked examples).
- Phase 3 — Analytics/ML: Webster calculator using survey PCU + data/signal_timings.csv; v/c per approach; 15-min demand forecaster (trained on 11 May, evaluated on 12 May); YOLO counter deferred.
- Phase 4 — Dashboard screens 1–4 + PDF export; role-based OTP login.
- Phase 5 — Plan Studio: POST /plans/simulate runs SUMO headless; UI compares before/after.
- Phase 6 — AI Copilot (local Ollama, read-only SQL tools, returns chart spec + SQL), Citizen reports, Event mode, monthly PDF (en + hi).

## Acceptance checklist

- [ ] `make infra` + `make sim` + `make api` + `pnpm dev:dashboard` run the full system locally
- [ ] 8 Mansarovar junctions stream live phases at 1 Hz
- [ ] Health Score and 5 metrics match hand calculations in tests
- [ ] Fairness audit ranks phases and exports a clean PDF
- [ ] All 8 junctions use the May 2026 survey counts, labelled "Survey"
- [ ] Plan Studio shows a before/after for one fixed-timer junction
- [ ] No endpoint can send a command to a signal (checked in code review)
- [ ] Source badge visible on every number
- [ ] Works on a laptop without internet during the demo (local mode)
