"""Field-study analysis (P8 W14): stops, travel time, time stopped and speed profile per run, then
advice ON vs OFF with bootstrap 95% confidence intervals, a permutation test and a power note.

Run on synthetic runs (SIM) to check the pipeline:   uv run python -m ml.study --synthetic
Run on the real study export (FIELD):                uv run python -m ml.study --export study_export.json
Writes services/ml/reports/field_study.md and field_study.json. If a CI crosses zero, it says so.
"""

import math
import random
from itertools import pairwise
from statistics import mean, stdev

from .geo import corridor, haversine_m, project

STOP_KMH, STOP_S = 5.0, 3.0  # a stop = below 5 km/h for at least 3 s (same rule as the app)
TRIM_M = 200.0


def trim(points: list[list[float]], trim_m: float = TRIM_M) -> list[list[float]]:
    """Same privacy rule as the API: drop the first and last 200 m of the path."""
    if len(points) < 2:
        return []
    cum = [0.0]
    for p, q in pairwise(points):
        cum.append(cum[-1] + haversine_m((p[1], p[2]), (q[1], q[2])))
    return [p for p, d in zip(points, cum, strict=True) if trim_m <= d <= cum[-1] - trim_m]


def run_metrics(points: list[list[float]]) -> dict:
    """Metrics between the first and the last junction of the corridor."""
    ch = corridor()["chainage"]
    proj = [project(p[1], p[2])[0] for p in points]
    east = proj[-1] >= proj[0]
    first, last = (ch[0], ch[-1]) if east else (ch[-1], ch[0])
    inside = [i for i, s in enumerate(proj) if min(first, last) <= s <= max(first, last)]
    if len(inside) < 10:
        return {"valid": False}
    seg = [points[i] for i in inside]
    stops, stopped_s, slow_since, counted = 0, 0.0, None, False
    for a, b in pairwise(seg):
        dt = b[0] - a[0]
        if b[3] < STOP_KMH:
            stopped_s += dt
            slow_since = a[0] if slow_since is None else slow_since
            if not counted and b[0] - slow_since >= STOP_S:
                stops, counted = stops + 1, True
        else:
            slow_since, counted = None, False
    bins: dict[int, list[float]] = {}
    for i in inside:
        bins.setdefault(int(abs(proj[i] - first) // 100), []).append(points[i][3])
    return {"valid": True, "travelTimeS": seg[-1][0] - seg[0][0], "stops": stops, "timeStoppedS": round(stopped_s, 1),
            "meanSpeedKmh": round(mean(p[3] for p in seg), 1), "profile": {k * 100: round(mean(v), 1) for k, v in sorted(bins.items())}}  # fmt: skip


def bootstrap_diff(a: list[float], b: list[float], n: int = 10_000, seed: int = 7) -> tuple[float, float]:
    """95% CI for mean(a) - mean(b), resampling runs within each arm."""
    rnd = random.Random(seed)
    diffs = sorted(mean(rnd.choices(a, k=len(a))) - mean(rnd.choices(b, k=len(b))) for _ in range(n))
    return diffs[int(0.025 * n)], diffs[int(0.975 * n) - 1]


def permutation_p(a: list[float], b: list[float], n: int = 10_000, seed: int = 11) -> float:
    """Two-sided p-value for a difference in means, shuffling the arm labels."""
    rnd = random.Random(seed)
    obs = abs(mean(a) - mean(b))
    pooled, k, hits = a + b, len(a), 0
    for _ in range(n):
        rnd.shuffle(pooled)
        hits += abs(mean(pooled[:k]) - mean(pooled[k:])) >= obs - 1e-12
    return (hits + 1) / (n + 1)


def min_detectable(sd: float, n_per_arm: int) -> float:
    """Smallest true difference detectable with 80% power at alpha = 0.05 (two-sided, normal approx.)."""
    return (1.96 + 0.84) * sd * math.sqrt(2 / n_per_arm)


def analyse(runs: list[dict], source: str) -> dict:
    rows = []
    for r in runs:
        m = run_metrics(trim(r["points"]))
        if m["valid"]:
            rows.append({**m, "arm": r["arm"], "participant": r["participant"]})
    out = {"source": source, "runs": len(rows), "byArm": {}, "compare": {}}
    for arm in ("advice", "control"):
        rs = [x for x in rows if x["arm"] == arm]
        out["byArm"][arm] = {
            "runs": len(rs),
            **{
                k: round(mean(x[k] for x in rs), 2) if rs else None
                for k in ("stops", "travelTimeS", "timeStoppedS", "meanSpeedKmh")
            },
        }
    for k in ("stops", "travelTimeS", "timeStoppedS"):
        a = [x[k] for x in rows if x["arm"] == "advice"]
        b = [x[k] for x in rows if x["arm"] == "control"]
        if len(a) < 2 or len(b) < 2:
            continue
        lo, hi = bootstrap_diff(a, b)
        sd = math.sqrt((stdev(a) ** 2 + stdev(b) ** 2) / 2)
        out["compare"][k] = {"diff": round(mean(a) - mean(b), 2), "ci95": [round(lo, 2), round(hi, 2)], "crossesZero": lo <= 0 <= hi,
                             "relative": round(100 * (mean(a) - mean(b)) / mean(b), 1) if mean(b) else None,
                             "pPermutation": round(permutation_p(a, b), 4), "minDetectable": round(min_detectable(sd, min(len(a), len(b))), 2)}  # fmt: skip
    out["perRun"] = rows
    return out
