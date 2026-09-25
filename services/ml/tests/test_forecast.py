"""Forecaster: MAPE helper by hand, and a leakage-free train/test split (needs tmc_clean)."""

import numpy as np
import pytest

from ml import data, forecast


def test_mape_excludes_small_actuals() -> None:
    # Actual 4 < 5 is skipped. Remaining errors: |11-10|/10 = 0.10, |15-20|/20 = 0.25 -> mean 17.5 %.
    out = forecast.mape(np.array([10.0, 4.0, 20.0]), np.array([11.0, 100.0, 15.0]))
    assert out == {"mape": 17.5, "n": 2, "excluded": 1}


needs_tmc = pytest.mark.skipif(not data.TMC_AVAILABLE, reason="tmc_clean.csv is local-only and missing")


@needs_tmc
def test_features_have_no_target_leakage() -> None:
    ds = forecast.build_datasets()
    x, y = ds["x_test"], ds["y_test"]
    lag1 = forecast.FEATURES.index("lag1")
    prev = forecast.FEATURES.index("prev_day")
    # prev_day on the test day is exactly the 11-May same slot (= the seasonal naive baseline).
    assert np.array_equal(x[:, prev], ds["baseline"])
    # lag1 of slot s is the actual of slot s-1 on 12 May (same movement), never slot s itself.
    for i in range(1, 96):
        assert x[i, lag1] == y[i - 1]
    # Only J03-J08 (surveyed on both days); 72 movement series x 96 slots.
    assert {k[0] for k in ds["keys"]} == {"J03", "J04", "J05", "J06", "J07", "J08"}
    assert len(y) == 72 * 96


@needs_tmc
def test_evaluate_shape() -> None:
    ev = forecast.evaluate()
    assert set(ev["junctions"]) == {"J03", "J04", "J05", "J06", "J07", "J08"}
    for v in ev["junctions"].values():
        assert v["baseline_mape"] >= 0 and v["model_mape"] >= 0
    assert ev["corridor"]["pooled"]["n"] + ev["corridor"]["pooled"]["excluded"] == ev["n_test"]
