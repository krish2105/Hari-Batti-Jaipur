# HariBatti — demand forecasting and anomaly detection (W5)

> Generated 2026-09-26 11:09 IST · 15-minute-ahead forecasts of vehicles per junction movement (J03–J08) · MAE and RMSE in vehicles per 15 min, WAPE = total absolute error ÷ total vehicles

## 1. Real survey data — only 2 days, so be careful

**Data-quality finding:** the 12 May counts correlate 0.9999 with 11 May, 27% of movement-slots are exactly identical and the median ratio is 1.029. 12 May looks largely derived from 11 May, so it is not an independent test day: the naive and profile baselines look near-perfect for that reason, not because traffic is that predictable. This question has been raised for the survey agency (data/README.md).

Train: Survey 11 May 2026 (1 day) (6,624 movement-slots). Test: Survey 12 May 2026 (1 day) (6,912). 72 movements. **Survey, May 2026.**

| Model | MAE | RMSE | WAPE |
| --- | --- | --- | --- |
| Seasonal naive (same slot yesterday) (baseline) | 3.05 | 4.59 | 2.6% |
| Last value (previous 15 min) (baseline) | 15.93 | 32.00 | 13.7% |
| Level-adjusted profile (baseline) | 1.04 | 2.05 | **0.9%** |
| LightGBM (1 training day) | 10.62 | 20.21 | 9.2% |

LightGBM WAPE 9.2% vs the best baseline (Level-adjusted profile) 0.9%. It does **not** beat the baseline, but one training day and one test day prove nothing about next month: no deep-learning claim is made on real data.

## 2. SIM data — 8 generated weeks

SIM weeks 1-6 (generated from the 11 May survey profile); SIM week 8 (week 7 used for early stopping and conformal calibration). 241,920 training and 48,384 test movement-slots. **SIM: trained on simulated data.** The generator (ml/w5/simdemand.py) starts from the 11 May survey profile and adds ASSUMED weekday factors, day and slot noise, rain days, evening events and labelled incidents; results show whether the pipeline works, not how accurate it would be on real weeks.

| Model | MAE | RMSE | WAPE |
| --- | --- | --- | --- |
| Seasonal naive (same slot yesterday) (baseline) | 19.04 | 39.45 | 17.5% |
| Weekly naive (same slot last week) (baseline) | 17.58 | 37.02 | 16.2% |
| Weekday profile (training weeks) (baseline) | 12.25 | 25.48 | 11.3% |
| LightGBM | 12.14 | 23.47 | **11.2%** |
| GWN-lite (Graph WaveNet-style, simplified) | 15.72 | 31.35 | 14.5% |

GWN-lite: 21,281 parameters, trained 12 epochs on mps, best epoch chosen on week 7.

### Calibrated uncertainty (split conformal, SIM)

A ±29.0-vehicle band around the LightGBM forecast, sized on week 7, covered **89.9%** of week-8 movement-slots (target 90%).

### What drives the LightGBM forecast (mean |SHAP|, SIM test week)

| Feature | Mean abs SHAP |
| --- | --- |
| week_ago | 0.698 |
| day_ago | 0.303 |
| lag1 | 0.291 |
| mean4 | 0.078 |
| lag2 | 0.055 |
| lag4 | 0.043 |
| slot_sin | 0.024 |
| dow | 0.024 |

## 3. Anomaly detection

On SIM week 8 with injected anomalies on movements carrying at least 10 vehicles per 15 min: event recall **83%** (6 injected: incidents 100%, surges 50%, closures 100%). Alarm precision **28%** (29 alarms; an alarm = consecutive flagged slots on one movement), slot precision 42% (57 slots). Rain days and evening events are real but unlabelled, so some alarms counted as false are genuine. Poisson z-score rules (closed, drop, surge) + isolation forest (scikit-learn)

Real survey (12 May vs the 11 May profile) — top findings, **Survey, May 2026**:

| Junction | Time | Kind | Deviation | What |
| --- | --- | --- | --- | --- |

## Honest limitations

- Two survey days: real-data results are one train day and one test day; they cannot show weekly or seasonal skill.
- The SIM weeks come from a generator with ASSUMED patterns, so SIM accuracy is an upper bound on what the pipeline could do with real weeks of counts (from the CV pipeline or an ITMS feed).
- GWN-lite is a small, simplified Graph WaveNet-style model (dilated causal convolutions + graph convolution), not the full published architecture.

Reproduce: `cd services/ml && uv run --group forecast python -m ml.w5.run`
