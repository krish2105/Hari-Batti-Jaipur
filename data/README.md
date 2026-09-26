# Data guide

| Path | What | Rows | Notes |
| --- | --- | --- | --- |
| raw/tmc/DAY1_8J/ | 8 workbooks, 11 May 2026 (Mon) | — | Files 3–8 are identical copies of INT_11-05-2026 01–06 with different approach labels |
| raw/tmc/INT_11-05-2026/ | TMC-01..06, 11 May 2026 (Mon) | — | Used for J03–J08 day 1 |
| raw/tmc/INT_12-05-2026/ | TMC-01..06, 12 May 2026 (Tue) | — | Used for J03–J08 day 2 |
| processed/tmc_clean.csv | 1 row per junction × day × movement × 15-min slot | 16,128 | Deduplicated; slow totals recomputed |
| processed/junction_day_summary.csv | Daily totals, % two-wheelers, AM/PM peak hour PCU + PHF | 14 | |
| processed/pm_peak_approach_turns.csv | PCU/hr by approach and turn (L/S/R) in the PM peak | 56 | |
| processed/hourly_profile_pcu.csv | Hourly PCU per junction-day | 336 | Simulator demand + website charts |
| junction_registry.csv | J01–J08 master list | 8 | Fill lat, lng, lanes, signal_type, cycle |
| signal_timings.csv | Your stopwatch timings (template) | — | Delete the EXAMPLE row |
| junctions.geojson | J01–J08 points for maps (built from the registry) | 8 | `verify: true` = placeholder position |
| junction_coords_candidates.csv | CANDIDATE lat/lng from OpenStreetMap (`make sim-coords`) | ≤24 | Not verified. Check on Google Maps, then copy into the registry yourself |
| osm/*.osm | OpenStreetMap extract for the simulator (gitignored) | — | © OpenStreetMap contributors, ODbL |

## tmc_clean.csv columns
junction_id, junction_name, tmc_code, survey_date, day, source_file, movement (1–12), from_approach, to_approach,
turn (L/S/R), slot (0 = 08:00–08:15 … 95 = 07:45–08:00 next day), start, car_taxi_auto_pickup, two_wheeler,
tractor_lcv_minibus, axle_truck_bus, truck_trailer_mav, total_fast, cycle, cycle_rickshaw, hand_cart,
horse_drawn, bullock_cart, total_slow (recomputed), total_veh (recomputed), total_pcu (as surveyed), total_slow_reported.

## Known data issues
1. Duplicates: DAY1_8J files 3–8 = INT_11-05-2026 01–06 (identical numbers). Only one copy is used.
2. Label mismatch: the same counts carry different cross-road names in the two versions
   (e.g. J04: "Madhyam Marg / Muhana Mandi" vs "Durgapur / Mohanpura"). Confirm on the ground.
3. File "1 SFS RIICO" says "2 SFS RIICO" inside. Treated as J01.
4. The survey's "Total Slow" column misses 2,032 vehicles in 372 of 23,040 rows; recomputed from its parts.
   PCU values are used as surveyed.
5. "Horse Drawn" shows 1–2% of traffic at several junctions, which is unusually high for Mansarovar;
   the column may hold e-rickshaws or carts. Ask the survey agency.
6. Peak-hour factors of 0.92–0.99 are very flat; plausible for saturated junctions but worth checking.
7. **12 May looks largely derived from 11 May (J03–J08).** Across all 72 movements × 96 slots the two days
   correlate 0.9999, 27% of movement-slots are exactly identical and the median ratio is 1.03 (computed by
   `services/ml/ml/w5/run.py`). Real traffic on two weekdays is never this similar. Ask the survey agency whether
   12 May was counted separately. Until then, 12 May is **not** an independent validation day: the W1
   validation score, the W2 held-out results and the real-data forecast scores all overstate skill.

## Filling the registry (used by the simulator)
- `lat`, `lng`: decimal degrees. When all 8 rows have both, `make sim-calibrate` switches from the
  schematic network to the real OpenStreetMap roads automatically.
- `lanes_per_approach`: either one number for every arm (`3`) or per approach, using the names in
  `approaches_used`: `Mansarover Metro:3 | Sanganer Stadium:3 | Durgapur:2 | Mohanpura:2`.
  Blank = the assumptions in `services/sim/assumptions.toml` (flagged in every report).

## signal_timings.csv format
One row per phase. `approaches_served` lists approaches (names from `approaches_used`) with optional
turns, separated by `;` — e.g. `Mansarover Metro (S+L); Sanganer Stadium (S+L)`. No turns = all turns.
Rows whose `notes` contain `EXAMPLE` are ignored. A junction with no real rows uses a labelled
"Assumed timing" plan.
