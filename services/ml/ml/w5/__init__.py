"""W5 forecasting and anomaly detection.

simdemand.py  8 weeks of SIM demand generated from the 11 May survey profile with injected variability
models.py     baselines, LightGBM, a simplified Graph WaveNet-style network, split-conformal intervals
anomaly.py    isolation forest + rules, scored on injected SIM anomalies, then run on the real survey
run.py        trains everything and writes reports/forecasting.md, forecast.json, anomalies.json
Honest ML: every model reports a baseline, a held-out metric and its data size. Deep learning is
trained and tested on SIM data only (2 real survey days are far too few).
"""
