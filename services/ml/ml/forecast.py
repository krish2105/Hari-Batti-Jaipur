"""15-minute demand forecaster: trained on 11 May 2026, tested on 12 May 2026 (J03-J08).

Target: total vehicles per junction movement per 15-min slot (Survey, May 2026, tmc_clean.csv).
J01/J02 are left out because they were only surveyed on 11 May.

Baseline  "seasonal naive": 12 May slot s = 11 May slot s (same movement).
Model     scikit-learn HistGradientBoostingRegressor (Poisson loss, fixed seed) with features that
          are all known BEFORE the slot starts (no leakage from the target slot):
            - slot-of-day sin / cos
            - movement ID (junction + movement 1-12) as a categorical feature
            - lag1, lag2: the same movement's count in the previous two 15-min slots of the same
              timeline (for 12 May slot 0 that is 11 May slots 95 and 94, i.e. 07:30-08:00 on 12 May)
            - prev_day: the same movement's 11-May count in the same slot
Training uses only 11 May rows. There is no day before 11 May, so for training rows prev_day is
stood in by the mean of the neighbouring 11-May slots (s-1, s+1), never slot s itself. Training
rows start at slot 2 so both lags exist inside 11 May.

MAPE skips slots whose actual count is below 5 vehicles (tiny counts make percentages explode);
the number skipped is reported.
"""

import math

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

from . import data

TRAIN_DATE = "2026-05-11"
TEST_DATE = "2026-05-12"
SLOTS = 96
MIN_ACTUAL_FOR_MAPE = 5
FEATURES = ("slot_sin", "slot_cos", "movement_id", "lag1", "lag2", "prev_day")


def _series() -> dict[tuple[str, int], dict[str, np.ndarray]]:
    """{(junction, movement): {date: 96 counts}} for junctions surveyed on both days."""
    out: dict[tuple[str, int], dict[str, np.ndarray]] = {}
    for r in data.load_tmc():
        if r["survey_date"] not in (TRAIN_DATE, TEST_DATE):
            continue
        key = (r["junction_id"], r["movement"])
        days = out.setdefault(key, {})
        arr = days.setdefault(r["survey_date"], np.zeros(SLOTS))
        arr[r["slot"]] += r["total_veh"]
    return {k: v for k, v in sorted(out.items()) if TRAIN_DATE in v and TEST_DATE in v}


def _feature_row(slot: int, movement_id: int, lag1: float, lag2: float, prev_day: float) -> list[float]:
    """One feature vector in FEATURES order."""
    angle = 2 * math.pi * slot / SLOTS
    return [math.sin(angle), math.cos(angle), movement_id, lag1, lag2, prev_day]


def build_datasets() -> dict:
    """Training rows (11 May) and test rows (12 May) with features, targets and baselines."""
    series = _series()
    x_train, y_train, x_test, y_test, base, keys = [], [], [], [], [], []
    for mid, (key, days) in enumerate(series.items()):
        d1, d2 = days[TRAIN_DATE], days[TEST_DATE]
        timeline = np.concatenate([d1, d2])  # 11-May slot 95 is directly followed by 12-May slot 0
        for s in range(2, SLOTS):
            neighbours = [d1[s - 1]] + ([d1[s + 1]] if s + 1 < SLOTS else [])
            x_train.append(_feature_row(s, mid, d1[s - 1], d1[s - 2], float(np.mean(neighbours))))
            y_train.append(d1[s])
        for s in range(SLOTS):
            i = SLOTS + s
            x_test.append(_feature_row(s, mid, timeline[i - 1], timeline[i - 2], d1[s]))
            y_test.append(d2[s])
            base.append(d1[s])
            keys.append((key[0], key[1], s))
    return {
        "x_train": np.array(x_train),
        "y_train": np.array(y_train),
        "x_test": np.array(x_test),
        "y_test": np.array(y_test),
        "baseline": np.array(base),
        "keys": keys,
    }


def train_model(x_train: np.ndarray, y_train: np.ndarray) -> HistGradientBoostingRegressor:
    """Fit the gradient-boosting model (movement ID treated as a category)."""
    cat = [f == "movement_id" for f in FEATURES]
    model = HistGradientBoostingRegressor(
        loss="poisson", categorical_features=cat, max_iter=300, learning_rate=0.05, random_state=0
    )
    return model.fit(x_train, y_train)


def mape(actual: np.ndarray, predicted: np.ndarray, min_actual: float = MIN_ACTUAL_FOR_MAPE) -> dict:
    """Mean absolute percentage error over slots with actual >= min_actual.

    Returns {"mape": percent or None, "n": slots used, "excluded": slots skipped}.
    """
    keep = actual >= min_actual
    n = int(keep.sum())
    value = float(np.mean(np.abs(predicted[keep] - actual[keep]) / actual[keep]) * 100) if n else None
    return {"mape": None if value is None else round(value, 2), "n": n, "excluded": int((~keep).sum())}


def evaluate() -> dict:
    """Train on 11 May, test on 12 May. MAPE per junction and for the corridor, baseline vs model.

    corridor.pooled         -> every movement-slot of J03-J08 together
    corridor.total_series   -> the corridor's summed 15-min volume (96 slots)
    """
    ds = build_datasets()
    model = train_model(ds["x_train"], ds["y_train"])
    pred = model.predict(ds["x_test"])
    actual, base = ds["y_test"], ds["baseline"]
    junctions = np.array([k[0] for k in ds["keys"]])
    slots = np.array([k[2] for k in ds["keys"]])
    per_junction = {}
    for jid in sorted(set(junctions)):
        m = junctions == jid
        b, p = mape(actual[m], base[m]), mape(actual[m], pred[m])
        per_junction[jid] = {
            "baseline_mape": b["mape"],
            "model_mape": p["mape"],
            "n": b["n"],
            "excluded": b["excluded"],
        }
    pooled_b, pooled_p = mape(actual, base), mape(actual, pred)
    tot_a = np.array([actual[slots == s].sum() for s in range(SLOTS)])
    tot_b = np.array([base[slots == s].sum() for s in range(SLOTS)])
    tot_p = np.array([pred[slots == s].sum() for s in range(SLOTS)])
    return {
        "train_date": TRAIN_DATE,
        "test_date": TEST_DATE,
        "target": "total_veh per junction movement per 15-min slot",
        "data_label": data.SURVEY_LABEL,
        "model": "HistGradientBoostingRegressor (poisson loss)",
        "features": list(FEATURES),
        "n_train": len(ds["y_train"]),
        "n_test": len(actual),
        "mape_note": f"Slots with actual < {MIN_ACTUAL_FOR_MAPE} vehicles are excluded from MAPE.",
        "junctions": per_junction,
        "corridor": {
            "pooled": {
                "baseline_mape": pooled_b["mape"],
                "model_mape": pooled_p["mape"],
                "n": pooled_b["n"],
                "excluded": pooled_b["excluded"],
            },
            "total_series": {
                "baseline_mape": mape(tot_a, tot_b)["mape"],
                "model_mape": mape(tot_a, tot_p)["mape"],
                "n": SLOTS,
            },
        },
    }
