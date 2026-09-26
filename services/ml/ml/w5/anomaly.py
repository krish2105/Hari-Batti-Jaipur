"""Anomaly detection on 15-min counts: isolation forest + explainable rules.

For every movement-slot we compare the count with what was expected (a profile) using a Poisson
z-score, z = (actual - expected) / sqrt(expected + 1). Rules name the anomaly:
  closed / dark approach  actual 0 while at least 10 were expected, 2 slots in a row
  sudden drop             z below -4 for 2 slots in a row
  surge                   z above +4 for 2 slots in a row
An isolation forest (scikit-learn), trained on normal weeks, adds "unusual pattern" when the
combination of z, the ratio and the neighbouring slots looks unlike training (contamination 0.2%).
Expectations are first adjusted to each junction's level over the previous hour (level_adjust).
Live signal faults (stuck phase, dark signal, flashing amber by day) are detected from the phase
stream in the dashboard live wall; this module covers counts.
"""

import numpy as np
from sklearn.ensemble import IsolationForest


def level_adjust(actual: np.ndarray, expected: np.ndarray, groups: np.ndarray, window: int = 4) -> np.ndarray:
    """Scale each row's expectation by how busy its group (junction) was over the previous `window`
    slots, relative to plan (causal: never uses the slot being judged). Corridor-wide rain or a
    junction-wide event then moves the expectation instead of flooding the alarms, while one
    movement's incident or closure still stands out against its busy neighbours."""
    out = expected.copy()
    for g in np.unique(groups):
        rows = groups == g
        a, e = actual[rows].sum(axis=0), expected[rows].sum(axis=0)
        ca, ce = np.concatenate([[0.0], np.cumsum(a)]), np.concatenate([[0.0], np.cumsum(e)])
        for k in range(window, actual.shape[1]):
            den = ce[k] - ce[k - window]
            if den > 0:
                out[rows, k] *= np.clip((ca[k] - ca[k - window]) / den, 0.6, 1.6)
    return out


def zscores(actual: np.ndarray, expected: np.ndarray, cv: float = 0.0) -> np.ndarray:
    """Over-dispersed z-score: variance = expected + (cv x expected)^2 (Poisson plus a multiplicative
    day/slot variability cv, as in a negative-binomial model). cv = 0 gives the plain Poisson z."""
    e = np.clip(expected, 0, None)
    return (actual - e) / np.sqrt(e + (cv * e) ** 2 + 1.0)


def fit_dispersion(actual: np.ndarray, expected: np.ndarray, min_expected: float = 20.0) -> float:
    """Multiplicative variability cv estimated from normal (training) data on busy movement-slots."""
    busy = expected >= min_expected
    extra = ((actual[busy] - expected[busy]) ** 2 - expected[busy]) / expected[busy] ** 2
    return float(np.sqrt(max(0.0, np.mean(extra))))


def _features(actual: np.ndarray, expected: np.ndarray, cv: float = 0.0) -> np.ndarray:
    z = zscores(actual, expected, cv)
    prev = np.concatenate([z[:, :1], z[:, :-1]], axis=1)
    nxt = np.concatenate([z[:, 1:], z[:, -1:]], axis=1)
    ratio = np.log((actual + 1) / (expected + 1))
    return np.stack([z, prev, nxt, ratio], axis=-1).reshape(-1, 4)


def rules(
    actual: np.ndarray, expected: np.ndarray, zmax: float = 4.0, cv: float = 0.0
) -> dict[tuple[int, int], str]:
    """{(row, step): kind} for rule hits (two consecutive slots needed)."""
    z = zscores(actual, expected, cv)
    hits: dict[tuple[int, int], str] = {}
    for kind, mask in (
        ("closed", (actual == 0) & (expected >= 10)),
        ("drop", z < -zmax),
        ("surge", z > zmax),
    ):
        both = mask[:, 1:] & mask[:, :-1]
        for r, c in zip(*np.nonzero(both), strict=True):
            hits.setdefault((int(r), int(c)), kind)
            hits.setdefault((int(r), int(c) + 1), kind)
    return hits


def detect(actual: np.ndarray, expected: np.ndarray, train_actual: np.ndarray, train_expected: np.ndarray,
           seed: int = 0) -> dict[tuple[int, int], tuple[str, float]]:  # fmt: skip
    """{(row, step): (kind, score)} combining the rules and the isolation forest. The forest only raises
    an alarm where the over-dispersed z is also beyond 4.5, so it cannot fill a fixed quota of alarms."""
    cv = fit_dispersion(train_actual, train_expected)
    forest = IsolationForest(n_estimators=200, contamination=0.002, random_state=seed)
    forest.fit(_features(train_actual, train_expected, cv))
    feats = _features(actual, expected, cv)
    score = -forest.score_samples(feats).reshape(actual.shape)
    z = zscores(actual, expected, cv)
    flag = (forest.predict(feats).reshape(actual.shape) == -1) & (np.abs(z) > 4.5)
    out = {k: (v, float(score[k])) for k, v in rules(actual, expected, cv=cv).items()}
    for r, c in zip(*np.nonzero(flag), strict=True):
        out.setdefault((int(r), int(c)), ("unusual pattern", float(score[r, c])))
    return out


def score_injected(found: dict, injected: list[dict], offset: int, steps: int, expected: np.ndarray | None = None,
                   min_expected: float = 0.0) -> dict:  # fmt: skip
    """Over [offset, offset+steps): event recall (an injected anomaly is found if any of its slots is
    flagged), alarm precision (an alarm = a run of consecutive flagged slots on one movement; true if
    it touches an injected window) and slot precision (share of flagged slots inside a window)."""
    windows = [a for a in injected if offset <= a["start"] < offset + steps]
    if expected is not None and min_expected > 0:  # count only events on movements busy enough to see
        windows = [a for a in windows if expected[a["rows"], a["start"] - offset].mean() >= min_expected]
    inside = {
        (r, s - offset)
        for a in windows
        for r in a["rows"]
        for s in range(a["start"], a["start"] + a["length"])
    }
    hit = sum(
        1
        for a in windows
        if any(
            (r, s - offset) in found for r in a["rows"] for s in range(a["start"], a["start"] + a["length"])
        )
    )
    tp = sum(1 for k in found if k in inside)
    alarms, true_alarms = 0, 0
    for r, c in sorted(found):
        if (r, c - 1) in found:
            continue  # not the start of an alarm
        alarms += 1
        k = c
        touched = False
        while (r, k) in found:
            touched |= (r, k) in inside
            k += 1
        true_alarms += touched
    return {
        "recall": hit / max(1, len(windows)),
        "alarmPrecision": true_alarms / max(1, alarms),
        "precision": tp / max(1, len(found)),
        "n": len(windows),
        "alarms": alarms,
        "flagged": len(found),
    }
