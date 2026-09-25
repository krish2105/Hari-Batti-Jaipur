# HariBatti analytics report (P5a)

Counts: Survey, May 2026 (aggregates only). Read-only analysis: nothing here controls a signal.

## v/c per approach, peak hours of 2026-05-11 (Survey, May 2026)

capacity = saturation flow x lanes x g / C; v/c > 0.9 is flagged. Under the assumed 2-phase plan left turns run free, so the flow is S + R PCU/h. One fixed plan per junction (built from its PM-peak counts) is used for both peaks.

Timing: Assumed timing – demand-proportional (2-phase, free left).
Lanes: ASSUMED from services/sim/assumptions.toml (main 3, cross 2) where the registry is blank.

### AM peak

| Junction | Approach | Hour | Flow PCU/h | Lanes | g/C (s) | Capacity | v/c | Flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| J01 | B2BYPASS | 09:00 | 2,304 | 3 (ASSUMED) | 60/180 | 1,800 | 1.28 | over 0.9 |
| J01 | RICCO | 09:00 | 2,006 | 2 (ASSUMED) | 110/180 | 2,200 | 0.91 | over 0.9 |
| J01 | SHIPRA PATH | 09:00 | 2,028 | 2 (ASSUMED) | 110/180 | 2,200 | 0.92 | over 0.9 |
| J01 | SUMER NAGAR | 09:00 | 966 | 3 (ASSUMED) | 60/180 | 1,800 | 0.54 |  |
| J02 | B2BYPASS | 12:00 | 2,658 | 3 (ASSUMED) | 32/60 | 2,880 | 0.92 | over 0.9 |
| J02 | MADHYAM MARG | 12:00 | 670 | 2 (ASSUMED) | 18/60 | 1,080 | 0.62 |  |
| J02 | SFS | 12:00 | 456 | 2 (ASSUMED) | 18/60 | 1,080 | 0.42 |  |
| J02 | SUMER NAGAR | 12:00 | 1,406 | 3 (ASSUMED) | 32/60 | 2,880 | 0.49 |  |
| J03 | Mansarover Metro | 09:00 | 1,702 | 3 (ASSUMED) | 27/60 | 2,430 | 0.70 |  |
| J03 | Patrika Gate | 09:00 | 662 | 2 (ASSUMED) | 23/60 | 1,380 | 0.48 |  |
| J03 | Sanganer Stadium | 09:00 | 3,044 | 3 (ASSUMED) | 27/60 | 2,430 | 1.25 | over 0.9 |
| J03 | Sumer Nagar | 09:00 | 1,710 | 2 (ASSUMED) | 23/60 | 1,380 | 1.24 | over 0.9 |
| J04 | Durgapur | 09:15 | 829 | 2 (ASSUMED) | 19/60 | 1,140 | 0.73 |  |
| J04 | Mansarover Metro | 09:15 | 2,604 | 3 (ASSUMED) | 31/60 | 2,790 | 0.93 | over 0.9 |
| J04 | Mohanpura | 09:15 | 966 | 2 (ASSUMED) | 19/60 | 1,140 | 0.85 |  |
| J04 | Sanganer Stadium | 09:15 | 1,812 | 3 (ASSUMED) | 31/60 | 2,790 | 0.65 |  |
| J05 | Mansarover Metro | 09:15 | 2,884 | 3 (ASSUMED) | 38/60 | 3,420 | 0.84 |  |
| J05 | Patel Marg Crossing | 09:15 | 302 | 2 (ASSUMED) | 12/60 | 720 | 0.42 |  |
| J05 | Sanganer Stadium | 09:15 | 2,570 | 3 (ASSUMED) | 38/60 | 3,420 | 0.75 |  |
| J05 | Sumer Nagar | 09:15 | 598 | 2 (ASSUMED) | 12/60 | 720 | 0.83 |  |
| J06 | Dholai | 11:30 | 1,548 | 2 (ASSUMED) | 45/117 | 1,385 | 1.12 | over 0.9 |
| J06 | Mansarover Metro | 11:30 | 2,336 | 3 (ASSUMED) | 62/117 | 2,862 | 0.82 |  |
| J06 | Sanganer Stadium | 11:30 | 2,632 | 3 (ASSUMED) | 62/117 | 2,862 | 0.92 | over 0.9 |
| J06 | VT Road | 11:30 | 808 | 2 (ASSUMED) | 45/117 | 1,385 | 0.58 |  |
| J07 | Mangyawas | 09:45 | 484 | 2 (ASSUMED) | 15/82 | 658 | 0.73 |  |
| J07 | Mansarover Metro | 09:45 | 4,728 | 3 (ASSUMED) | 57/82 | 3,754 | 1.26 | over 0.9 |
| J07 | Rajatpath | 09:45 | 424 | 2 (ASSUMED) | 15/82 | 658 | 0.64 |  |
| J07 | Sanganer Stadium | 09:45 | 3,058 | 3 (ASSUMED) | 57/82 | 3,754 | 0.81 |  |
| J08 | Mansarover | 09:15 | 138 | 2 (ASSUMED) | 10/60 | 600 | 0.23 |  |
| J08 | Mansarover Metro | 09:15 | 2,423 | 3 (ASSUMED) | 40/60 | 3,600 | 0.67 |  |
| J08 | New Aatish Market | 09:15 | 388 | 2 (ASSUMED) | 10/60 | 600 | 0.65 |  |
| J08 | Sanganer Stadium | 09:15 | 3,014 | 3 (ASSUMED) | 40/60 | 3,600 | 0.84 |  |

### PM peak

| Junction | Approach | Hour | Flow PCU/h | Lanes | g/C (s) | Capacity | v/c | Flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| J01 | B2BYPASS | 18:30 | 2,014 | 3 (ASSUMED) | 60/180 | 1,800 | 1.12 | over 0.9 |
| J01 | RICCO | 18:30 | 1,226 | 2 (ASSUMED) | 110/180 | 2,200 | 0.56 |  |
| J01 | SHIPRA PATH | 18:30 | 2,433 | 2 (ASSUMED) | 110/180 | 2,200 | 1.11 | over 0.9 |
| J01 | SUMER NAGAR | 18:30 | 870 | 3 (ASSUMED) | 60/180 | 1,800 | 0.48 |  |
| J02 | B2BYPASS | 19:00 | 2,254 | 3 (ASSUMED) | 32/60 | 2,880 | 0.78 |  |
| J02 | MADHYAM MARG | 19:00 | 832 | 2 (ASSUMED) | 18/60 | 1,080 | 0.77 |  |
| J02 | SFS | 19:00 | 586 | 2 (ASSUMED) | 18/60 | 1,080 | 0.54 |  |
| J02 | SUMER NAGAR | 19:00 | 1,834 | 3 (ASSUMED) | 32/60 | 2,880 | 0.64 |  |
| J03 | Mansarover Metro | 18:15 | 1,558 | 3 (ASSUMED) | 27/60 | 2,430 | 0.64 |  |
| J03 | Patrika Gate | 18:15 | 1,154 | 2 (ASSUMED) | 23/60 | 1,380 | 0.84 |  |
| J03 | Sanganer Stadium | 18:15 | 1,976 | 3 (ASSUMED) | 27/60 | 2,430 | 0.81 |  |
| J03 | Sumer Nagar | 18:15 | 916 | 2 (ASSUMED) | 23/60 | 1,380 | 0.66 |  |
| J04 | Durgapur | 18:15 | 939 | 2 (ASSUMED) | 19/60 | 1,140 | 0.82 |  |
| J04 | Mansarover Metro | 18:15 | 2,235 | 3 (ASSUMED) | 31/60 | 2,790 | 0.80 |  |
| J04 | Mohanpura | 18:15 | 873 | 2 (ASSUMED) | 19/60 | 1,140 | 0.77 |  |
| J04 | Sanganer Stadium | 18:15 | 2,309 | 3 (ASSUMED) | 31/60 | 2,790 | 0.83 |  |
| J05 | Mansarover Metro | 18:30 | 2,500 | 3 (ASSUMED) | 38/60 | 3,420 | 0.73 |  |
| J05 | Patel Marg Crossing | 18:30 | 574 | 2 (ASSUMED) | 12/60 | 720 | 0.80 |  |
| J05 | Sanganer Stadium | 18:30 | 2,861 | 3 (ASSUMED) | 38/60 | 3,420 | 0.84 |  |
| J05 | Sumer Nagar | 18:30 | 528 | 2 (ASSUMED) | 12/60 | 720 | 0.73 |  |
| J06 | Dholai | 18:30 | 1,294 | 2 (ASSUMED) | 45/117 | 1,385 | 0.94 | over 0.9 |
| J06 | Mansarover Metro | 18:30 | 2,440 | 3 (ASSUMED) | 62/117 | 2,862 | 0.85 |  |
| J06 | Sanganer Stadium | 18:30 | 2,670 | 3 (ASSUMED) | 62/117 | 2,862 | 0.93 | over 0.9 |
| J06 | VT Road | 18:30 | 480 | 2 (ASSUMED) | 45/117 | 1,385 | 0.35 |  |
| J07 | Mangyawas | 18:30 | 370 | 2 (ASSUMED) | 15/82 | 658 | 0.56 |  |
| J07 | Mansarover Metro | 18:30 | 3,412 | 3 (ASSUMED) | 57/82 | 3,754 | 0.91 | over 0.9 |
| J07 | Rajatpath | 18:30 | 576 | 2 (ASSUMED) | 15/82 | 658 | 0.88 |  |
| J07 | Sanganer Stadium | 18:30 | 2,739 | 3 (ASSUMED) | 57/82 | 3,754 | 0.73 |  |
| J08 | Mansarover | 18:30 | 124 | 2 (ASSUMED) | 10/60 | 600 | 0.21 |  |
| J08 | Mansarover Metro | 18:30 | 2,178 | 3 (ASSUMED) | 40/60 | 3,600 | 0.60 |  |
| J08 | New Aatish Market | 18:30 | 452 | 2 (ASSUMED) | 10/60 | 600 | 0.75 |  |
| J08 | Sanganer Stadium | 18:30 | 2,608 | 3 (ASSUMED) | 40/60 | 3,600 | 0.72 |  |

15 of 64 approach-peaks have v/c > 0.9.

## 15-min demand forecast: train 11 May, test 12 May (J03-J08)

Target: total_veh per junction movement per 15-min slot (Survey, May 2026). Model: HistGradientBoostingRegressor (poisson loss) with features slot_sin, slot_cos, movement_id, lag1, lag2, prev_day. Baseline: seasonal naive (12 May slot = 11 May slot). Slots with actual < 5 vehicles are excluded from MAPE. Train rows 6768, test rows 6912.

| Junction | Baseline MAPE % | Model MAPE % | Slots used | Slots excluded |
| --- | --- | --- | --- | --- |
| J03 | 2.84 | 6.14 | 1075 | 77 |
| J04 | 4.47 | 7.49 | 1069 | 83 |
| J05 | 5.71 | 8.11 | 1027 | 125 |
| J06 | 3.00 | 6.91 | 1086 | 66 |
| J07 | 5.10 | 7.55 | 926 | 226 |
| J08 | 7.15 | 8.90 | 973 | 179 |
| Corridor (all movement-slots) | 4.65 | 7.49 | 6156 | 756 |
| Corridor total per slot | 2.05 | 1.83 | 96 | 0 |

The model beats the seasonal naive baseline at 0 of 6 junctions (movement level). Limitation: only one training day exists, so the model never sees a real 'previous day' value while training (a neighbouring-slot stand-in is used), and two survey days are too few to judge day-to-day variation.
