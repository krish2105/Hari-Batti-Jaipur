"""HariBatti analytics/ML package (read-only; never controls a signal).

Modules:
  ml.data      shared loaders (registry, lanes, assumptions, processed survey CSVs)
  ml.webster   Webster cycle/greens, d1/d2 delay, the assumed 2-phase free-left plan
  ml.capacity  capacity and v/c per approach at the AM/PM peak
  ml.metrics   the five Junction Health metrics and the Health Score
  ml.forecast  15-min demand forecaster (train 11 May, test 12 May 2026)
Run `python -m ml report` for the analytics report.
"""
