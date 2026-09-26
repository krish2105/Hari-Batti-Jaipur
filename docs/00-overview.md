# HariBatti 00 — Overview

HariBatti ("green light") is a **read-only** citizen and audit layer on top of Jaipur's traffic
signals: live countdowns for drivers, and an audit that shows traffic police where red waits run
long and greens run short. It never controls a signal.

## The problem

- Long red waits: older fixed cycles of 60–90 s run regardless of traffic.
- Starved greens: some phases are too short to clear the queue, so riders wait 2–3 cycles and
  some jump the red.
- Short pedestrian clearance on wide roads (Tonk Road, JLN Marg).
- No visibility: a driver 500 m away cannot know when the light will change.
- Jaipur drivers lost about 121 rush-hour hours each in 2025 (TomTom Traffic Index).

Jaipur Police is rolling out AI-ITMS signal control (the Rambagh Circle trial saved 8–45 s per
lane; 253 of 423 junctions are next). HariBatti is designed to sit alongside that system: it
reads phase data, it does not replace or compete with signal control.

## Products (one backend, three front-ends)

| # | Product | User | Spec |
| --- | --- | --- | --- |
| 1 | 3D showcase website | Police, officials, the public | [01-website.md](01-website.md) |
| 2 | Signal Command dashboard | Traffic DCP, Abhay Command Centre | [02-dashboard.md](02-dashboard.md) |
| 3 | HariBatti mobile app | Drivers, riders, pedestrians | [03-mobile.md](03-mobile.md) |

## Pilot: Mansarovar corridor (J01–J08)

The pilot corridor runs between Mansarovar Metro and Sanganer Stadium, where professional
24-hour classified turning-movement counts exist for 8 junctions (11 and 12 May 2026).
Findings are in [05-data-analysis.md](05-data-analysis.md).

| ID | Junction | Survey code | Days counted |
| --- | --- | --- | --- |
| J01 | SFS RIICO | — | 1 |
| J02 | SFS Agrawal | — | 1 |
| J03 | Jansunvai | TMC-01 | 2 |
| J04 | Vijay Path | TMC-02 | 2 |
| J05 | Patel Marg | TMC-03 | 2 |
| J06 | VT Road | TMC-04 | 2 |
| J07 | Rajat Path | TMC-05 | 2 |
| J08 | Bhrigu Path | TMC-06 | 2 |

**Still to collect in the field:** signal timings (stopwatch, 10 cycles per junction at AM and
PM peak), lanes and stop-line widths per approach, verified junction coordinates.

**Pilot scope (proposed):** read-only access to live phase and countdown data for the 8 pilot
junctions; no control rights; data stays in India; police own all data and reports; the pilot
can be switched off at any time.

**What the pilot measures (design goals, not results):**

| Metric | Baseline method | Target |
| --- | --- | --- |
| Degree of saturation (v/c) per approach | Survey peak PCU ÷ capacity from timings + lanes | Flag every approach above 0.9 |
| Average red wait per approach | Stopwatch timings + survey arrivals | −15% via recommended splits |
| Stops per corridor trip (J03→J08) | GPS test drives | −20% with green-wave advice |
| Pedestrian clearance vs crossing width | Tape + timer | 100% at 1.0–1.2 m/s |
| App timer accuracy | App vs physical signal | Under 2 s with a live feed |

## Architecture

One monorepo, one signal data model, and a **PhaseSource** interface that reads from the
simulator today, crowd estimates next, and the police ITMS feed once a data-sharing agreement
exists. Every front-end reads the same API, so swapping the source changes nothing downstream.

```
apps/web         Next.js + React Three Fiber showcase (deployed on Vercel)
apps/dashboard   Next.js police Signal Command dashboard
apps/mobile      Expo (React Native) app
services/api     FastAPI: REST + WebSocket /ws/signals, PostGIS, Redis
services/sim     SUMO digital twin of the corridor + calibration
services/ml      Webster, v/c, health metrics, forecasting, optimisation
services/cv      Computer vision (counts, queues, saturation flow)
packages/core    Shared types (Junction, PhaseState, DataSource) + GLOSA speed advice
packages/ui      Design tokens
```

Data model (`packages/core`): `Junction`, `Approach`, `PhaseState` with
`source: "SIM" | "CROWD" | "ITMS"`, and `DataSource = SIM | FIELD | SURVEY | CROWD | ITMS`
labels on every number.

## Safety and data rules

- Read-only everywhere: no code path sends a command to a signal controller or police system.
- App advice is only "hold X km/h", "prepare to stop" or "red, X seconds" — never "go" — and is
  capped at the speed limit minus 5 km/h. The physical signal always wins.
- Voice-first; no taps while moving.
- Traffic volumes come only from the survey (`data/processed/*.csv`); raw survey sheets are
  confidential and never published — public outputs use aggregates only.
- Zero paid APIs; the AI copilot runs on local Ollama.
- Privacy: DPDP Act 2023 consent, location only during a ride, no identity tracking, no ANPR,
  faces and plates blurred in any video pipeline.
- Independent project, not affiliated with Rajasthan Police or Jaipur Traffic Police.

## Sources

- Jaipur AI signals at 253 intersections — pinkcitypost.com
- Tonk Road model corridor — pinkcitypost.com
- TomTom Traffic Index, Jaipur — tomtom.com/traffic-index/city/jaipur
- Low-cost intelligent signals with IUDX — iudx.org.in
- GLOSA (A45 trial) — interregeurope.eu
