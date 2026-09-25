# HariBatti 05 — Traffic Count Analysis (Mansarovar corridor, May 2026)

Built from 20 survey workbooks by `scripts/process_tmc.py`. All figures are from the survey data; PCU = passenger car units as reported by the survey.

## What the data is

Professional classified turning-movement counts (TMC): every vehicle counted by class, by turn (12 movements per junction), in 15-minute bins for 24 hours (08:00 to 08:00).

| Item | Value |
| --- | --- |
| Unique junctions | 8 (J01–J08) |
| Survey days | Mon 11 May 2026 (all 8); Tue 12 May 2026 (J03–J08) |
| Junction-days | 14 |
| Clean rows | 16,128 (junction × day × movement × 15-min) |
| Vehicle classes | 5 fast + 5 slow, plus PCU |
| Duplicates removed | 6 files (DAY1_8J 3–8 = INT_11-05-2026 01–06) |

## Headline numbers (Monday 11 May)

| ID | Junction | 24-h vehicles | 24-h PCU | Two-wheelers | AM peak | AM PCU/hr | PM peak | PM PCU/hr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| J01 | SFS RIICO | 176,546 | 138,245 | 47.9% | 09:00 | 10,363 | 18:30 | 9,340 |
| J02 | SFS Agrawal | 125,444 | 109,496 | 45.3% | 12:00 | 6,363 | 19:00 | 6,836 |
| J03 | Jansunvai | 127,998 | 111,706 | 42.5% | 09:00 | 8,930 | 18:15 | 7,392 |
| J04 | Vijay Path | 129,047 | 109,140 | 49.4% | 09:15 | 7,288 | 18:15 | 7,270 |
| J05 | Patel Marg | 128,195 | 102,357 | 54.0% | 09:15 | 6,894 | 18:30 | 7,187 |
| J06 | VT Road | 153,323 | 124,861 | 51.2% | 11:30 | 8,570 | 18:30 | 8,307 |
| J07 | Rajat Path | 127,981 | 101,201 | 48.9% | 09:45 | 9,269 | 18:30 | 7,972 |
| J08 | Bhrigu Path | 114,811 | 91,562 | 48.3% | 09:15 | 6,849 | 18:30 | 6,331 |

Peak times are the start of the busiest rolling hour. Tuesday volumes were 1.7–3.7% higher than Monday at every junction with two days, with near-identical peak times (within 30 minutes).

## Key findings

1. **Very heavy, very flat peaks.** 6,300–10,400 PCU/hr through a single junction, with peak-hour factors of 0.92–0.99. Demand stays near the top for the whole hour, which is typical of junctions running at or near capacity.
2. **The main road dominates.** At J04–J08 the Mansarovar Metro ↔ Sanganer Stadium approaches carry 66–90% of PM-peak PCU; the busiest single movement is always the straight-through main-road flow (2,265–3,040 PCU/hr). Green time that is split evenly with side streets would be wasted.
3. **Six signals in a row on one arterial (J03→J08).** Through-traffic is the biggest movement at almost every junction, so a coordinated green wave plus speed advice is the natural fix.
4. **Two-wheelers are about half of all traffic (42–54%).** This justifies the app's Rider mode and voice-first design.
5. **Right turns are 12–24% of PM-peak PCU at J03–J08** (32% at J01). These need their own protected phases and are a likely cause of short, starved greens.
6. **Two peaks:** 09:00–10:00 is the corridor's busiest hour overall; the evening peak is 18:15–19:15. J06 VT Road and J02 SFS Agrawal peak late morning (11:30 and 12:00), worth a site check.
7. **Night is quiet** (02:00–04:00 under 1,500 vehicles/hr at most junctions), which supports flashing-amber or short-cycle night plans.

## Data quality issues (fixed or flagged)

| Issue | Action |
| --- | --- |
| DAY1_8J files 3–8 duplicate INT_11-05-2026 files 01–06 | Used one copy only |
| Same counts carry different cross-road names in the two versions | Flagged in data/junction_registry.csv; confirm on site |
| "1 SFS RIICO" file says "2 SFS RIICO" inside | Treated as J01 |
| Survey "Total Slow" misses 2,032 vehicles in 372 rows | Recomputed from class columns; totals now match the survey's own 24-h table |
| "Horse Drawn" at 1–2% of traffic | Likely e-rickshaws or carts; ask the survey agency |
| No signal timings in the files | Collect with stopwatch → data/signal_timings.csv |

## What this unlocks now vs after signal timings

| Now (counts only) | After timings + lanes |
| --- | --- |
| Realistic simulator demand, 15-min by turn | Degree of saturation (v/c) per approach |
| Website and dashboard charts with real numbers | Average red wait and cycles-to-clear |
| Peak-hour and turn-share insights for the pitch | Webster optimal cycle and green splits |
| Demand forecaster (train Mon, test Tue) | Before/after simulation of better plans and green wave |

## Pitch line

"We have 24-hour counts for 8 of your Mansarovar junctions. Up to 90% of peak traffic is on the main road, six signals in a row. Give us the signal timings and we will show you, junction by junction, where green time does not match demand."
