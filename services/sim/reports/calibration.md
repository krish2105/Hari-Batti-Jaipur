# HariBatti simulator — calibration & validation report

> **Schematic network – coordinates pending**  
> Timing: **Assumed timing – demand-proportional (2-phase, free left)** (ASSUMED — no field timings yet)  
> Generated 2026-09-26 14:17 IST · simulated 24 h from 08:00 IST in 90.7 min · SUMO sublane model on

**Method:** the survey day is scored as 8 three-hour windows run in parallel, each after a 30-minute warm-up (a continuous 24-h run never recovers from the morning backlog; see Gridlock). Counts marked **Survey, May 2026** come from `data/processed/tmc_clean.csv` (hourly aggregates only); **SIM** is simulated. GEH = √(2(M−C)²/(M+C)). Target: GEH < 5 for at least 85% of movement-hours. Hour 08–09 has no earlier traffic to warm up from and is shown but not scored.

## Summary

| Junction | Calibration (11 May) GEH<5 | Result | Validation (12 May) GEH<5 | Result |
| --- | --- | --- | --- | --- |
| J08 | 56% | FAIL | 54% | FAIL |
| J07 | 40% | FAIL | 38% | FAIL |
| J06 | 39% | FAIL | 39% | FAIL |
| J05 | 43% | FAIL | 42% | FAIL |
| J04 | 47% | FAIL | 47% | FAIL |
| J03 | 58% | FAIL | 57% | FAIL |
| J01 | 59% | FAIL | no 12 May data | — |
| J02 | 49% | FAIL | no 12 May data | — |
| **Corridor** | **49%** | **FAIL** | **46%** (J03–J08) | **FAIL** |

## Gridlock

| Window | Vehicles loaded | Still waiting to enter at the end | Share | Teleports |
| --- | --- | --- | --- | --- |
| 08:00 + 3 h | 94,764 | 34,672 | 37% | 1,596 |
| 11:00 + 3 h | 101,665 | 51,413 | 51% | 3,263 |
| 14:00 + 3 h | 85,149 | 14,631 | 17% | 1,250 |
| 17:00 + 3 h | 106,632 | 46,731 | 44% | 2,303 |
| 20:00 + 3 h | 82,409 | 13,991 | 17% | 1,634 |
| 23:00 + 3 h | 31,017 | 2,119 | 7% | 27 |
| 02:00 + 3 h | 10,830 | 0 | 0% | 2 |
| 05:00 + 3 h | 44,827 | 2,083 | 5% | 80 |
| **Day** | **557,293** | **165,640** | **30%** | **10,155** |

### One continuous run (why the day is scored in windows)

The same network run continuously from 08:00: vehicles still waiting to enter at the end of each hour. The backlog never drains, so a continuous run measures the queue, not the network.

| Until | Waiting to enter |
| --- | --- |
| 09:00 | 2,539 |
| 10:00 | 18,619 |
| 11:00 | 34,672 |
| 12:00 | 50,216 |
| 13:00 | 69,819 |
| 14:00 | 86,288 |
| 15:00 | 101,222 |
| 16:00 | 113,936 |
| 17:00 | 130,252 |
| 18:00 | 144,950 |

## Hourly GEH<5 share (calibration, 11 May)

| Hour | J08 | J07 | J06 | J05 | J04 | J03 | J01 | J02 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 08-09 (not scored) | 83% | 33% | 50% | 67% | 50% | 42% | 58% | 42% |
| 09-10 | 25% | 0% | 17% | 33% | 33% | 8% | 25% | 33% |
| 10-11 | 25% | 0% | 17% | 25% | 25% | 25% | 42% | 33% |
| 11-12 | 25% | 0% | 17% | 0% | 17% | 25% | 0% | 0% |
| 12-13 | 33% | 0% | 0% | 0% | 25% | 33% | 0% | 17% |
| 13-14 | 42% | 25% | 0% | 33% | 17% | 25% | 8% | 25% |
| 14-15 | 50% | 42% | 25% | 33% | 42% | 67% | 75% | 58% |
| 15-16 | 58% | 17% | 50% | 50% | 67% | 67% | 83% | 50% |
| 16-17 | 33% | 8% | 42% | 33% | 33% | 42% | 75% | 42% |
| 17-18 | 42% | 8% | 33% | 25% | 33% | 58% | 0% | 33% |
| 18-19 | 17% | 0% | 17% | 25% | 25% | 33% | 25% | 25% |
| 19-20 | 25% | 0% | 17% | 25% | 17% | 25% | 8% | 8% |
| 20-21 | 83% | 42% | 8% | 17% | 50% | 58% | 75% | 50% |
| 21-22 | 50% | 50% | 25% | 25% | 25% | 17% | 83% | 58% |
| 22-23 | 58% | 58% | 17% | 42% | 50% | 58% | 75% | 67% |
| 23-00 | 58% | 100% | 50% | 50% | 67% | 83% | 58% | 83% |
| 00-01 | 67% | 83% | 58% | 75% | 50% | 92% | 83% | 75% |
| 01-02 | 83% | 50% | 83% | 83% | 75% | 83% | 83% | 75% |
| 02-03 | 83% | 58% | 42% | 83% | 75% | 100% | 100% | 67% |
| 03-04 | 83% | 75% | 83% | 67% | 58% | 100% | 100% | 67% |
| 04-05 | 83% | 83% | 67% | 58% | 58% | 100% | 100% | 83% |
| 05-06 | 75% | 100% | 50% | 58% | 67% | 92% | 100% | 75% |
| 06-07 | 100% | 67% | 100% | 67% | 100% | 75% | 83% | 50% |
| 07-08 | 92% | 50% | 83% | 83% | 83% | 58% | 83% | 42% |

## 15 worst movement-hours (calibration, 11 May)

| Junction | Movement | Hour | Survey, May 2026 | SIM | GEH |
| --- | --- | --- | --- | --- | --- |
| J07 | Mansarover Metro → Sanganer Stadium (S) | 10-11 | 5,809 | 116 | 104.6 |
| J07 | Mansarover Metro → Sanganer Stadium (S) | 09-10 | 5,402 | 131 | 100.2 |
| J07 | Sanganer Stadium → Mansarover Metro (S) | 10-11 | 3,579 | 105 | 80.9 |
| J07 | Sanganer Stadium → Mansarover Metro (S) | 09-10 | 3,686 | 169 | 80.1 |
| J05 | Mansarover Metro → Sanganer Stadium (S) | 09-10 | 3,853 | 299 | 78.0 |
| J07 | Mansarover Metro → Sanganer Stadium (S) | 11-12 | 3,992 | 436 | 75.6 |
| J07 | Mansarover Metro → Sanganer Stadium (S) | 18-19 | 3,097 | 101 | 74.9 |
| J07 | Sanganer Stadium → Mansarover Metro (S) | 11-12 | 3,245 | 175 | 74.2 |
| J07 | Sanganer Stadium → Mansarover Metro (S) | 18-19 | 2,961 | 77 | 74.0 |
| J06 | Sanganer Stadium → Mansarover Metro (S) | 18-19 | 3,093 | 128 | 73.9 |
| J08 | Sanganer Stadium → Mansarover Metro (S) | 10-11 | 3,125 | 148 | 73.6 |
| J05 | Sanganer Stadium → Mansarover Metro (S) | 19-20 | 3,181 | 176 | 73.3 |
| J08 | Sanganer Stadium → Mansarover Metro (S) | 09-10 | 3,114 | 189 | 72.0 |
| J05 | Mansarover Metro → Sanganer Stadium (S) | 10-11 | 3,209 | 268 | 70.5 |
| J08 | Mansarover Metro → Sanganer Stadium (S) | 10-11 | 2,835 | 132 | 70.2 |

## Unserved demand

Vehicles never inserted by the end of the run: **30%** of the demand loaded (target < 5%) — **FAIL**.

**Caution on validation:** the 12 May survey counts are almost a copy of 11 May (correlation 0.9999, 27% of movement-slots identical; data/README.md issue 7), so the 12 May score is not an independent check.

## What is FIELD and what is ASSUMED

| Input | Value used | Source |
| --- | --- | --- |
| Traffic counts (demand, vehicle mix) | Survey, May 2026 | FIELD (professional 24-h turning counts) |
| Junction positions | Schematic straight line | ASSUMED (OSM candidates unverified) |
| Spacing between junctions | 500 m | ASSUMED |
| Lanes per direction | main 4, cross 3 (effective, from the search) | ASSUMED (±1 of 3 / 2; not measured) |
| Signal timings | Assumed timing – demand-proportional plans | ASSUMED |
| Saturation flow (plans) | 1,800 PCU/h/lane | ASSUMED |
| Driver headway τ, speed factor | 1.0 s, 1.0 | ASSUMED (searched within physical bounds) |
| Two-wheeler lateral gap | 0.3 m | ASSUMED (searched) |

## Diagnostics: saturation flow SUMO actually achieves

One signalised test road with a standing queue (survey vehicle mix); literature for mixed Indian traffic: about 1,800–2,400 PCU/h of green per lane.

| Setting | PCU per hour of green per lane |
| --- | --- |
| survey mix, sublane on | 1,909 |
| survey mix, sublane off | 1,384 |
| cars only, sublane off | 1,446 |

With the sublane model on, SUMO discharges queues at a realistic rate, so saturation flow is not why the network jams; lane capacity and the schematic layout are.

## Diagnostics: what moved the score (same windows as the search: 09-10, 13-14, 18-19)

| Variant | Change | Calibration 11 May GEH<5 | Validation 12 May GEH<5 | Unserved | Teleports |
| --- | --- | --- | --- | --- | --- |
| V0 | Starting point: midblock access stubs on, 3 / 2 lanes | 28% | 20% | 42% | 924 |
| V1 | Midblock stubs off (no survey basis) | 35% | 28% | 32% | 414 |
| V2 | V1 + dedicated right-turn lane | 31% | 25% | 36% | 484 |
| V3 | V1 + one more lane per direction (4 / 3) | 47% | 44% | 19% | 773 |
| V4 | V3 + dedicated right-turn lane | 22% | 21% | 52% | 2,654 |

## Calibration search (Optuna, TPE)

30 completed trials over physically bounded parameters. Each trial is scored on 11 May only; 12 May is logged for honesty and never used to choose. Best: trial 1 (47%).

| Trial | Main / cross lanes | τ (s) | 2W gap (m) | Speed factor | Turn lanes | Calibration 11 May | Validation 12 May | Unserved |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 4 / 3 | 1.00 | 0.30 | 1.00 | auto | 47% | 44% | 19% |
| 20 | 4 / 3 | 0.95 | 0.17 | 1.04 | auto | 42% | 34% | 12% |
| 27 | 3 / 3 | 0.99 | 0.14 | 1.01 | auto | 42% | 37% | 21% |
| 5 | 3 / 3 | 1.11 | 0.38 | 0.95 | auto | 42% | 34% | 22% |
| 14 | 3 / 3 | 1.11 | 0.32 | 0.94 | auto | 42% | 39% | 23% |
| 31 | 4 / 3 | 0.97 | 0.19 | 1.04 | auto | 42% | 32% | 17% |
| 26 | 4 / 3 | 0.95 | 0.26 | 0.99 | auto | 41% | 35% | 12% |
| 29 | 4 / 3 | 1.06 | 0.14 | 1.05 | auto | 41% | 35% | 22% |
| 24 | 4 / 3 | 0.91 | 0.14 | 1.04 | auto | 40% | 33% | 6% |
| 22 | 3 / 3 | 1.03 | 0.24 | 1.01 | auto | 40% | 31% | 24% |
| 23 | 4 / 3 | 0.92 | 0.38 | 1.05 | auto | 40% | 33% | 8% |
| 25 | 4 / 2 | 1.09 | 0.29 | 1.05 | auto | 39% | 34% | 27% |

## Demand fit before simulation (routeSampler)

- Survey turning vehicles (11 May): **1,083,345**; routes written: **487,921**
- Static route fit: GEH<5 for 82% of counted movements per 15 min

## Counted flow per assumed lane (busiest hour, Survey, May 2026)

| Approach | Lanes (sim) | Busiest hour | Vehicles/h | Per lane |
| --- | --- | --- | --- | --- |
| J01 SHIPRA PATH | 3 | 18-19 | 5,071 | 1,690 |
| J07 Mansarover Metro | 4 | 10-11 | 6,177 | 1,544 |
| J08 Mansarover Metro | 4 | 09-10 | 4,339 | 1,085 |
| J07 Sanganer Stadium | 4 | 09-10 | 4,304 | 1,076 |
| J05 Mansarover Metro | 4 | 09-10 | 4,254 | 1,064 |
| J02 B2BYPASS | 4 | 13-14 | 4,223 | 1,056 |
| J03 Sanganer Stadium | 4 | 09-10 | 4,008 | 1,002 |
| J05 Sanganer Stadium | 4 | 19-20 | 3,918 | 980 |
| J01 B2BYPASS | 4 | 09-10 | 3,888 | 972 |
| J06 Dholai | 3 | 09-10 | 2,872 | 957 |
| J06 Mansarover Metro | 4 | 09-10 | 3,828 | 957 |
| J08 Sanganer Stadium | 4 | 09-10 | 3,761 | 940 |

## Timing plan used (ASSUMED)

| Junction | Cycle (s) | Greens (s) |
| --- | --- | --- |
| J08 | 60 | 40, 10 |
| J07 | 60 | 40, 10 |
| J06 | 60 | 30, 20 |
| J05 | 60 | 39, 11 |
| J04 | 60 | 32, 18 |
| J03 | 60 | 28, 22 |
| J01 | 63 | 20, 33 |
| J02 | 60 | 34, 16 |

## Flags

- Schematic network – coordinates pending (no lat/lng in data/junction_registry.csv)
- J03–J08 drawn in a straight row, 500 m apart (assumed spacing)
- Row order J08 (Mansarovar Metro end) … J03 (Sanganer Stadium end), taken from OpenStreetMap (Madhyam Marg crossings; Metro station in the New Aatish Market area) — verify with real coordinates
- J01–J02 drawn as a separate pair on the B2 Bypass side; link to J03 unknown, so none is drawn
- Arm positions (N/S of each cross road) derived from the survey's L/S/R labels, left-hand traffic
- No midblock access (no survey basis): count differences between neighbouring junctions stay unmatched
- Outer arms 400 m long (assumed)
- Lane use: netconvert defaults
- Lanes assumed at all 8 junctions (registry lanes_per_approach blank): main 4, cross 3
- Simulator calibrated (Optuna trial 1, 11 May only): main road 4 and cross road 3 effective lanes per direction — still ASSUMED (within +-1 of the 3 / 2 assumption); engineering metrics keep 3 / 2

## Why it fails, and what fixes it

- The network is a schematic straight line with ASSUMED 500 m spacing, lanes and timings; even the best search setting (one extra lane per direction) cannot carry the counted peak demand, so queues spill back and vehicles cannot enter.
- SUMO itself discharges queues at a realistic rate (see saturation flow), so the gap is geometry and capacity, not the traffic model.
- Next: verified junction coordinates (the OSM network is built automatically once the registry has them), measured lane counts and stopwatch timings (data/signal_timings.csv), then rerun this report. Nothing was tuned to force a pass, and 12 May was never used to choose.

Input hashes: `data/junction_registry.csv` fe62e596666aa170, `data/processed/tmc_clean.csv` e1bd2a6ab8cc7d0a, `data/processed/pm_peak_approach_turns.csv` d189d7b39a8347ff, `data/signal_timings.csv` 59a0636486365ac6, `services/sim/assumptions.toml` 4b9a86c2ac5b0574, `overrides` f087205e7339e84b
