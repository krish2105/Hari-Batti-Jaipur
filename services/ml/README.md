# services/ml

Analytics + ML from `data/processed/*.csv` (Survey, May 2026). Read-only: nothing here controls a signal.

| Module | What |
| --- | --- |
| `ml.data` | Loaders: registry, lanes (registry or ASSUMED), assumptions.toml, processed CSVs, `hourly_approach_pcu`, `TMC_AVAILABLE` |
| `ml.webster` | `webster_cycle`, `split_greens` (same as the simulator), `uniform_delay` (d1), `incremental_delay` (HCM 2000 d2), `two_phase_plan` |
| `ml.capacity` | `vc_table(date)` v/c per approach at AM/PM peak; `junction_timing`; `approach_hours(date)` for the metrics |
| `ml.metrics` | Five Junction Health metrics, `penalties`, `health_score`, `junction_metrics` |
| `ml.forecast` | 15-min demand forecaster, trained 11 May, tested 12 May (`evaluate()`) |

```
uv run python -m ml report   # prints tables, writes reports/analytics.md
uv run pytest -q
```

`data/processed/tmc_clean.csv` is local-only. Without it: PM v/c only, no forecaster, tmc tests skipped.

Use from another service: `haribatti-ml = { path = "../ml", editable = true }` under `[tool.uv.sources]`.
The repo root is found from the package location; set `HARIBATTI_ROOT` if the package is installed elsewhere.
