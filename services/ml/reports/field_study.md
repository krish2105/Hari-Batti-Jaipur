# HariBatti — field study: advice ON vs OFF (W14)

> **SIM** · 20 runs · generated 2026-09-26 12:08 UTC  
> A stop = below 5 km/h for at least 3 s. The first and last 200 m of every trace are removed before analysis.

**These are synthetic runs (SIM) that test the pipeline. They are not evidence**: the difference below comes
from the simulation's own driver model (80% of drivers follow a GLOSA speed within 400 m of a signal), not from
people. The real result needs the 20 GPS test drives with the app's Study mode.

| Arm | Runs | Stops per run | Travel time (s) | Time stopped (s) | Mean speed (km/h) |
| --- | --- | --- | --- | --- | --- |
| Advice ON | 10 | 0.4 | 383.9 | 10.9 | 34.7 |
| Advice OFF | 10 | 1.6 | 389.5 | 34.9 | 34.42 |

| Measure | ON − OFF | 95% CI (bootstrap) | Relative | Permutation p | Smallest detectable difference (80% power) |
| --- | --- | --- | --- | --- | --- |
| Stops per run | -1.2 | -2.1 to -0.4 | -75.0% | 0.0247 | 1.28 |
| Travel time J08→J03 | -5.6 s | -37.7 to 28.4 s | -1.4% | 0.7587 | 49.97 s |
| Time stopped | -24.0 s | -43.0 to -2.3 s | -68.8% | 0.0402 | 31.04 s |

- Stops per run: the 95% CI excludes zero (in simulation only).
- **Travel time J08→J03: the 95% CI crosses zero — no difference can be claimed.**
- Time stopped: the 95% CI excludes zero (in simulation only).

## Limits

- 20 runs detect only large effects (see the last column); runs by the same person are not independent, and
  the bootstrap resamples runs, so CIs are somewhat too narrow if people differ a lot.
- Junction positions and timings are ASSUMED until verified; the real study uses the live or stopwatch timings.
- Advice ON/OFF is assigned by the server in blocks of two per participant, so arms stay balanced.

Reproduce: `cd services/ml && uv run python -m ml.study --synthetic` (or `--export <file>` for real runs).
