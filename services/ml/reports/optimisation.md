# HariBatti — signal-timing optimisation (W2)

> **SIM** · Schematic network – coordinates pending · calibrated build cut to the J03-J08 corridor · ASSUMED timing  
> Trained on 2026-05-11 demand, evaluated on **2026-05-12** demand (a day no controller saw) · 18:00-19:00 after a 15-min warm-up (+15-min cool-down) · SUMO seeds 1, 2, 3, 4, 5 · mean ± 95% confidence half-width  
> Generated 2026-09-26 15:31 IST

Recommendations only: HariBatti never sends anything to a signal. An officer decides and applies any change in the real ITMS. The network is the schematic digital twin, calibrated only partly (full-day corridor GEH<5 49%, see services/sim/reports/calibration.md), with ASSUMED lanes and timings — read the **ranking**, not the absolute seconds.

## Corridor J03–J08, PM peak

| Controller | Kind | Runs | Travel time (s) | Waiting (s) | Stops | Queue (veh) | Throughput (veh/h) | CO₂ per trip (g) | Unserved (veh) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fixed time, even split 120 s (ASSUMED current) | fixed | 5 | 1,093.4 ± 36.7 | 795.2 ± 29.8 | 14.74 ± 0.49 | 2,223 ± 56 | 13,380 ± 316 | 1,368 ± 45 | 4,632 ± 132 |
| Webster, 2-phase with free left | fixed | 5 | 945.5 ± 84.4 | 681.2 ± 43.5 | 15.72 ± 1.79 | 1,922 ± 112 | 12,840 ± 261 | 1,290 ± 57 | 4,410 ± 579 |
| Webster, approach-wise (4 stages) | fixed | 5 | 872.9 ± 16.6 | 625.0 ± 13.2 | 8.43 ± 0.24 | 2,296 ± 34 | 15,527 ± 93 | 1,219 ± 20 | 2,472 ± 110 |
| Webster 2-phase + green-wave offsets | coordinated fixed | 5 | 941.9 ± 110.3 | 712.9 ± 97.1 | 13.72 ± 1.94 | 2,167 ± 253 | 12,525 ± 1,116 | 1,321 ± 163 | 4,439 ± 619 |
| MaxPressure | adaptive rule | 5 | 715.0 ± 71.5 | 428.4 ± 65.1 | 14.59 ± 1.00 | 1,390 ± 209 | 15,246 ± 763 | 1,003 ± 97 | 2,903 ± 491 |
| PPO, single-junction agent | reinforcement learning | 5 | 796.0 ± 51.1 | 504.9 ± 43.5 | 15.17 ± 1.08 | 1,558 ± 103 | 14,263 ± 444 | 1,065 ± 69 | 4,105 ± 399 |
| PPO, corridor agent (neighbour pressure) | reinforcement learning | 5 | 1,223.2 ± 231.4 | 953.5 ± 247.1 | 19.39 ± 1.87 | 2,666 ± 569 | 10,931 ± 2,022 | 1,662 ± 308 | 5,830 ± 1,484 |
| Fixed plan distilled from the corridor PPO | fixed (distilled) | 5 | 1,024.2 ± 105.2 | 773.5 ± 94.5 | 16.61 ± 2.35 | 2,289 ± 333 | 12,216 ± 1,136 | 1,427 ± 156 | 4,686 ± 672 |

Travel time includes time spent waiting to enter the network; trips still running at the end are counted, not dropped. Lowest mean travel time: **MaxPressure** (-35% vs Fixed time, even split 120 s (ASSUMED current)).

## Single junctions in isolation (same held-out day and window)

Each junction alone with its own surveyed turning counts. Mean travel time (s) ± 95% CI.

| Junction | Fixed time, even split 120 s (ASSUMED current) | Webster, 2-phase with free left | Webster, approach-wise (4 stages) | MaxPressure | PPO, single-junction agent |
| --- | --- | --- | --- | --- | --- |
| J08 | 956.9 ± 20.0 | 250.7 ± 3.7 | 329.4 ± 50.8 | 324.9 ± 13.9 | 227.9 ± 6.6 |
| J07 | 1,071.4 ± 15.8 | 303.4 ± 121.9 | 584.1 ± 28.8 | 293.8 ± 8.3 | 239.1 ± 44.3 |
| J06 | 1,229.9 ± 22.7 | 696.0 ± 494.7 | 989.5 ± 82.1 | 510.5 ± 88.3 | 495.0 ± 102.3 |
| J05 | 1,020.4 ± 15.2 | 316.9 ± 108.7 | 633.9 ± 93.7 | 294.1 ± 19.7 | 274.5 ± 8.3 |
| J04 | 787.9 ± 141.4 | 298.1 ± 79.1 | 572.9 ± 19.0 | 326.8 ± 143.2 | 333.5 ± 95.7 |
| J03 | 872.6 ± 344.6 | 333.8 ± 4.3 | 725.7 ± 433.2 | 341.1 ± 7.1 | 345.6 ± 5.4 |

## A plan an officer can key in (distilled from the corridor PPO agent)

The agent's stage choices on the training day, turned into one fixed plan per time of day: stages used at least 5% of the time, cycle from how often the main stage came back, greens in proportion to the time held. Amber 3 s + all-red 2 s after every stage. SIM, recommendation only.

### AM peak 08:00-11:00

| Junction | Cycle (s) | Stages (green s) |
| --- | --- | --- |
| J08 | 60 | Main road, straight + right (free left) 29; Cross road, straight + right (free left) 21 |
| J07 | 60 | Main road, straight + right (free left) 30; Cross road, straight + right (free left) 20 |
| J06 | 60 | Main road, straight + right (free left) 16; Cross road, straight + right (free left) 34 |
| J05 | 60 | Main road, straight + right (free left) 29; Cross road, straight + right (free left) 21 |
| J04 | 60 | Main road, straight + right (free left) 18; Cross road, straight + right (free left) 32 |
| J03 | 60 | Main road, straight + right (free left) 24; Cross road, straight + right (free left) 26 |

### Midday 12:00-15:00

| Junction | Cycle (s) | Stages (green s) |
| --- | --- | --- |
| J08 | 60 | Main road, straight + right (free left) 27; Cross road, straight + right (free left) 23 |
| J07 | 60 | Main road, straight + right (free left) 30; Cross road, straight + right (free left) 20 |
| J06 | 60 | Main road, straight + right (free left) 22; Cross road, straight + right (free left) 28 |
| J05 | 60 | Main road, straight + right (free left) 29; Cross road, straight + right (free left) 21 |
| J04 | 60 | Main road, straight + right (free left) 25; Cross road, straight + right (free left) 25 |
| J03 | 60 | Main road, straight + right (free left) 25; Cross road, straight + right (free left) 25 |

### PM peak 17:00-20:00

| Junction | Cycle (s) | Stages (green s) |
| --- | --- | --- |
| J08 | 60 | Main road, straight + right (free left) 32; Cross road, straight + right (free left) 18 |
| J07 | 60 | Main road, straight + right (free left) 34; Cross road, straight + right (free left) 16 |
| J06 | 60 | Main road, straight + right (free left) 20; Cross road, straight + right (free left) 30 |
| J05 | 60 | Main road, straight + right (free left) 28; Cross road, straight + right (free left) 22 |
| J04 | 60 | Main road, straight + right (free left) 24; Cross road, straight + right (free left) 26 |
| J03 | 60 | Main road, straight + right (free left) 25; Cross road, straight + right (free left) 25 |

## Green wave (coordinated offsets)

Common cycle **105 s** (Webster 2-phase green shares kept), progression speed 35 km/h, ASSUMED spacing 500 m. Offsets = when each junction's main-road green starts, in seconds into the cycle (same meaning as the dashboard time-space diagram).

| Junction | Distance from J08 (m) | Main green (s) | Offset (s) |
| --- | --- | --- | --- |
| J08 | 0 | 76 | 0 |
| J07 | 500 | 76 | 37 |
| J06 | 1,000 | 57 | 2 |
| J05 | 1,500 | 74 | 38 |
| J04 | 2,000 | 61 | 0 |
| J03 | 2,500 | 53 | 57 |

Green band: **51.5 s eastbound, 52.0 s westbound** per cycle, versus 1.5 s / 3.5 s with every offset 0 (today's assumption). The time-space diagram is on the dashboard (Plan Studio → Optimised).

## How it was done

- **Fixed plans** (even split, Webster 2-phase, Webster approach-wise) come from the simulator build; the green wave uses the Webster 2-phase greens rescaled to one common cycle.
- **MaxPressure** (Varaiya 2013) and **PPO** choose one of six stages every 6 s with a 10-s minimum green and 5 s of amber between stages, through the same sumo-rl mechanics.
- **PPO** (stable-baselines3, MIT) with sumo-rl (MIT): reward = intersection pressure (vehicles leaving − vehicles approaching); observation = stage, min-green flag, per-lane queue and density in and out; the corridor agent also sees its neighbours' pressure (PressLight-style) and shares one policy across the six junctions.
- `single-seed0`: 150,000 steps on 2026-05-11, 50 min on a laptop CPU, network [128, 128]
- `corridor-seed0`: 100,000 steps on 2026-05-11, 85 min on a laptop CPU, network [128, 128]

## Honest limitations

- Schematic geometry, ASSUMED 500 m spacing, lanes and timings; the twin reproduces only about half of the surveyed movement-hours (GEH<5), and the PM peak is oversaturated, so every controller leaves a queue. Differences between controllers matter more than the absolute seconds.
- Only two survey days exist: agents train on 11 May and are tested on 12 May, which is a similar weekday.
- Adaptive controllers need live detection (cameras or loops) that the pilot junctions do not have yet; the distilled fixed plan and the green-wave offsets are what could be tried first.
- Amber + all-red is lumped into 5 s of amber for the adaptive controllers (sumo-rl has no all-red).
- 12 May is almost a copy of 11 May in the survey (data/README.md issue 7), so the held-out day is not truly independent.
- The corridor PPO agent had only 100,000 training steps (about 85 min on a laptop CPU) and did worse than every fixed plan; it needs far more training before its ranking means anything. The single-junction agent (150,000 steps) is the one that learned something useful.
- The green wave does not help here: with the corridor oversaturated, queues from one junction block the next, so a band of green cannot be used. It becomes useful once capacity problems are fixed.

Reproduce: `cd services/sim && uv run --group rl python -m sim.opt.train single --seed 0` (and `corridor`), then `uv run --group rl python -m sim.opt.evaluate` and `uv run python -m sim.opt.report`.
