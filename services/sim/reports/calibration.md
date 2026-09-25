# HariBatti simulator — calibration & validation report

> **Schematic network – coordinates pending**  
> Timing: **Assumed timing – demand-proportional (2-phase, free left)** (ASSUMED — no field timings yet)  
> Generated 2026-09-26 02:51 IST · simulated 2 h from 08:00 IST in 8.9 min · SUMO sublane model on

Counts marked **Survey, May 2026** come from `data/processed/tmc_clean.csv` (hourly aggregates only). Counts marked **SIM** are simulated. GEH = √(2(M−C)²/(M+C)), M = SIM, C = Survey. Target: GEH < 5 for at least 85% of movement-hours. Hour 08–09 is warm-up (the network starts empty) and is shown but not scored.

## Summary

| Junction | Calibration (11 May) GEH<5 | Result | Validation (12 May) GEH<5 | Result |
| --- | --- | --- | --- | --- |
| J03 | 8% | FAIL | 8% | FAIL |
| J04 | 8% | FAIL | 8% | FAIL |
| J05 | 25% | FAIL | 8% | FAIL |
| J06 | 25% | FAIL | 25% | FAIL |
| J07 | 17% | FAIL | 8% | FAIL |
| J08 | 50% | FAIL | 33% | FAIL |
| J01 | 25% | FAIL | no 12 May data | — |
| J02 | 8% | FAIL | no 12 May data | — |
| **Corridor** | **21%** | **FAIL** | **15%** (J03–J08) | **FAIL** |

## Gridlock check

| Indicator | Value |
| --- | --- |
| Vehicles loaded (SIM demand in window) | 75,608 |
| Vehicles inserted | 39,350 |
| **Vehicles never inserted by end of run (unserved demand)** | **36,194** |
| Vehicles still driving at end | 5,748 |
| **Teleports** (jam / yield / wrong lane) | **534** (271 / 118 / 12) |

### Unserved demand by origin approach (vehicles waiting to enter at the end of each hour)

| Origin | 08-09 | 09-10 |
| --- | --- | --- |
| J01 SHIPRA PATH | 2,256 | 6,514 |
| J06 Dholai | 669 | 2,916 |
| J08 Sanganer Stadium | 237 | 2,877 |
| J01 B2BYPASS | 828 | 2,835 |
| J04 Mohanpura | 842 | 2,645 |
| J03 Mansarover Metro | 233 | 2,595 |
| J02 SUMER NAGAR | 1 | 2,430 |
| Midblock access M_J06_J07 | 323 | 2,168 |
| Midblock access M_J04_J05 | 870 | 1,769 |
| J03 Sumer Nagar | 393 | 1,615 |
| Midblock access M_J07_J08 | 742 | 1,377 |
| Midblock access M_J03_J04 | 955 | 1,100 |
| J02 MADHYAM MARG | 118 | 909 |
| J07 Mangyawas | 201 | 828 |
| J03 Patrika Gate | 117 | 775 |
| J05 Sumer Nagar | 171 | 678 |
| J06 VT Road | 219 | 606 |
| J01 RICCO | 18 | 563 |
| J08 New Aatish Market | 23 | 370 |
| J04 Durgapur | 0 | 258 |

### Teleports by approach

None.

### Max queue per approach (SIM, worst hour)

| Approach | Max queue (m, longest lane) | Max queued vehicles (all lanes) | Worst hour |
| --- | --- | --- | --- |
| J01 b2bypass | 389 | 155 | 08-09 |
| J08 sanganer-stadium | 389 | 335 | 09-10 |
| J02 sumer-nagar | 389 | 305 | 09-10 |
| J03 mansarover-metro | 389 | 317 | 09-10 |
| J04 mohanpura | 386 | 179 | 09-10 |
| J05 patel-marg-crossing | 386 | 180 | 09-10 |
| J03 patrika-gate | 386 | 175 | 09-10 |
| J02 sfs | 386 | 189 | 09-10 |
| J02 madhyam-marg | 386 | 165 | 09-10 |
| J05 sumer-nagar | 386 | 101 | 08-09 |
| J06 dholai | 386 | 196 | 09-10 |
| J03 sumer-nagar | 386 | 172 | 09-10 |
| J06 vt-road | 386 | 179 | 09-10 |
| J01 shipra-path | 386 | 161 | 08-09 |
| J04 durgapur | 386 | 175 | 09-10 |
| J08 new-aatish-market | 386 | 126 | 09-10 |
| J07 mangyawas | 386 | 183 | 09-10 |
| J07 rajatpath | 386 | 158 | 09-10 |
| J01 ricco | 385 | 160 | 08-09 |
| J03 sanganer-stadium | 229 | 142 | 08-09 |
| J04 mansarover-metro | 229 | 174 | 08-09 |
| J04 sanganer-stadium | 229 | 202 | 08-09 |
| J05 mansarover-metro | 229 | 214 | 08-09 |
| J05 sanganer-stadium | 229 | 208 | 09-10 |
| J06 mansarover-metro | 229 | 133 | 08-09 |
| J06 sanganer-stadium | 229 | 232 | 09-10 |
| J07 sanganer-stadium | 229 | 112 | 08-09 |
| J08 mansarover-metro | 229 | 206 | 09-10 |
| J01 sumer-nagar | 229 | 126 | 09-10 |
| J02 b2bypass | 229 | 195 | 09-10 |
| J08 mansarover | 156 | 67 | 09-10 |
| J07 mansarover-metro | 110 | 48 | 08-09 |

## Webster flow ratio Y per junction (PM peak, Survey, May 2026)

Y > 1 means no fixed cycle can serve the counted demand with the assumed lanes and saturation flow.

| Junction | 2-phase, free left | Approach-wise (4-stage) |
| --- | --- | --- |
| J03 | 0.69 | 1.62 — demand exceeds 4-stage capacity |
| J04 | 0.69 | 1.57 — demand exceeds 4-stage capacity |
| J05 | 0.69 | 1.46 — demand exceeds 4-stage capacity |
| J06 | 0.85 | 1.80 — demand exceeds 4-stage capacity |
| J07 | 0.79 | 1.60 — demand exceeds 4-stage capacity |
| J08 | 0.61 | 1.25 — demand exceeds 4-stage capacity |
| J01 | 1.05 — demand exceeds 2-phase capacity | 2.22 — demand exceeds 4-stage capacity |
| J02 | 0.65 | 1.44 — demand exceeds 4-stage capacity |

## Hourly GEH<5 share per junction (calibration, 11 May)

| Hour | J03 | J04 | J05 | J06 | J07 | J08 | J01 | J02 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 08-09 (warm-up) | 33% | 33% | 42% | 25% | 33% | 50% | 67% | 67% |
| 09-10 | 8% | 8% | 25% | 25% | 17% | 50% | 25% | 8% |

## 15 worst movement-hours (calibration, 11 May)

| Junction | Movement | Hour | Survey, May 2026 | SIM | GEH |
| --- | --- | --- | --- | --- | --- |
| J07 | Mansarover Metro → Sanganer Stadium (S) | 09-10 | 5,402 | 1,688 | 62.4 |
| J08 | Mansarover Metro → Sanganer Stadium (S) | 09-10 | 3,329 | 754 | 57.0 |
| J07 | Sanganer Stadium → Mansarover Metro (S) | 09-10 | 3,686 | 1,029 | 54.7 |
| J01 | B2BYPASS → SHIPRA PATH (R) | 09-10 | 2,165 | 328 | 52.0 |
| J05 | Sanganer Stadium → Mansarover Metro (S) | 09-10 | 3,000 | 817 | 50.0 |
| J01 | SHIPRA PATH → B2BYPASS (L) | 09-10 | 2,250 | 428 | 49.8 |
| J01 | SHIPRA PATH → SUMER NAGAR (R) | 09-10 | 1,359 | 64 | 48.5 |
| J05 | Mansarover Metro → Sanganer Stadium (S) | 09-10 | 3,853 | 1,387 | 48.2 |
| J06 | Mansarover Metro → Sanganer Stadium (S) | 09-10 | 2,730 | 776 | 46.7 |
| J06 | Sanganer Stadium → Mansarover Metro (S) | 09-10 | 2,453 | 629 | 46.5 |
| J08 | Sanganer Stadium → Mansarover Metro (S) | 09-10 | 3,114 | 1,012 | 46.3 |
| J02 | SUMER NAGAR → B2BYPASS (S) | 09-10 | 2,797 | 842 | 45.8 |
| J06 | Dholai → Mansarover Metro (L) | 09-10 | 1,524 | 220 | 44.2 |
| J01 | SHIPRA PATH → RICCO (S) | 09-10 | 1,322 | 205 | 40.4 |
| J03 | Mansarover Metro → Patrika Gate (L) | 09-10 | 1,358 | 359 | 34.1 |

## Timing plan used (ASSUMED)

| Junction | Cycle (s) | Greens (s) | Webster Y | Note |
| --- | --- | --- | --- | --- |
| J03 | 60 | 27, 23 | 0.69 |  |
| J04 | 60 | 31, 19 | 0.69 |  |
| J05 | 60 | 38, 12 | 0.69 |  |
| J06 | 117 | 62, 45 | 0.85 |  |
| J07 | 82 | 57, 15 | 0.79 |  |
| J08 | 60 | 40, 10 | 0.61 |  |
| J01 | 180 | 60, 110 | 1.05 | oversaturated: demand exceeds 2-phase capacity |
| J02 | 60 | 32, 18 | 0.65 |  |

## Assumptions and flags

- Schematic network – coordinates pending (no lat/lng in data/junction_registry.csv)
- J03–J08 drawn in a straight row, 500 m apart (assumed)
- J01–J02 drawn as a separate pair on the B2 Bypass side; link to J03 unknown, so none is drawn
- Arm positions (N/S of each cross road) derived from the survey's L/S/R labels, left-hand traffic
- One midblock access stub per shared link absorbs count differences between neighbouring junctions
- Outer arms 400 m long; access stubs 150 m (assumed)
- Lanes assumed at all 8 junctions (registry lanes_per_approach blank): main 3, cross 2
- Saturation flow 1800 PCU/h/lane, lost time 4 s/phase, amber 3 s, all-red 2 s
- Sublane model: lateral resolution 0.8 m; two-wheelers latAlignment=arbitrary, minGapLat=0.3 m
- Signal offsets are all 0 (no coordination yet); vehicle mix is the corridor-wide survey share
- Demand: routeSampler fitted 1,083,345 surveyed turning vehicles (11 May) with 384 candidate routes

## Data caveat

This is a schematic stand-in, not the real road layout: link lengths, lane counts, signal timings and coordination are assumptions until coordinates, lanes and stopwatch timings are collected. A FAIL here says the assumed network cannot reproduce the counts — most likely causes are capacity (lanes, saturation flow, phasing) and the midblock-access simplification — not that the survey is wrong. Nothing was tuned to force a pass.

Input hashes: `data/junction_registry.csv` fe62e596666aa170, `data/processed/tmc_clean.csv` e1bd2a6ab8cc7d0a, `data/processed/pm_peak_approach_turns.csv` d189d7b39a8347ff, `data/signal_timings.csv` 59a0636486365ac6, `services/sim/assumptions.toml` 7cd5a6f803d13c7f
