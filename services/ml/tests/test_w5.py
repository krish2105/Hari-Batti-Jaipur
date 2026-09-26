"""W5 pieces that need no LightGBM/torch: the SIM generator, conformal quantile and anomaly rules."""

import numpy as np

from ml.w5.simdemand import DAYS, SLOTS, generate


def _profile(n=6):
    slot = np.arange(SLOTS)
    return np.array([50 + 40 * np.sin(2 * np.pi * slot / SLOTS) + 10 * i for i in range(n)])


def test_generator_shape_seed_and_weekday_pattern():
    keys = [("J03", 1), ("J03", 2), ("J04", 1), ("J05", 1), ("J06", 1), ("J07", 1)]
    a = generate(_profile(), keys, seed=1)
    b = generate(_profile(), keys, seed=1)
    assert a.counts.shape == (6, DAYS * SLOTS)
    assert np.array_equal(a.counts, b.counts)  # reproducible
    daily = a.expected.reshape(6, DAYS, SLOTS).sum(axis=(0, 2))
    sundays, weekdays = daily[6::7].mean(), daily[0::7].mean()
    assert sundays < 0.85 * weekdays  # the Sunday factor shows through the noise


def test_injected_anomalies_are_labelled_and_visible():
    keys = [("J03", i) for i in range(1, 4)] + [("J05", i) for i in range(1, 4)]
    s = generate(_profile(), keys, seed=3)
    kinds = {a["kind"] for a in s.anomalies}
    assert kinds == {"incident", "surge", "closure"}
    closure = next(a for a in s.anomalies if a["kind"] == "closure")
    window = s.counts[closure["rows"], closure["start"] : closure["start"] + closure["length"]]
    assert window.sum() == 0


def test_conformal_quantile_and_rules():
    from ml.w5.anomaly import rules
    from ml.w5.models import conformal_q

    assert conformal_q(np.arange(1, 11, dtype=float), 0.9) == 10.0  # ceil(11*0.9)=10th smallest
    actual = np.array([[20, 0, 0, 20, 90, 100, 20]], float)
    expected = np.full((1, 7), 20.0)
    hits = rules(actual, expected)
    assert hits[(0, 1)] == "closed" and hits[(0, 2)] == "closed"
    assert hits[(0, 4)] == "surge" and (0, 0) not in hits


def test_level_adjust_absorbs_a_junction_wide_change_but_not_one_movement():
    from ml.w5.anomaly import level_adjust

    expected = np.full((4, 12), 100.0)
    actual = expected.copy()
    actual[:, 6:] = 70  # whole junction 30% down (rain): expectation follows after the window
    actual[0, 10:] = 5  # plus one movement nearly closed
    adj = level_adjust(actual, expected, np.array(["J05"] * 4))
    assert abs(adj[1, 11] - 70) < 10  # the rest of the junction is no longer "anomalous"
    assert actual[0, 11] < 0.2 * adj[0, 11]  # the closed movement still stands out


def test_alarm_precision_counts_runs_not_slots():
    from ml.w5.anomaly import score_injected

    injected = [{"kind": "incident", "rows": [0], "start": 10, "length": 4}]
    found = {(0, 10): "drop", (0, 11): "drop", (0, 12): "drop", (1, 30): "surge"}
    r = score_injected(found, injected, 0, 100)
    assert r["recall"] == 1.0 and r["alarms"] == 2 and r["alarmPrecision"] == 0.5 and r["precision"] == 0.75
