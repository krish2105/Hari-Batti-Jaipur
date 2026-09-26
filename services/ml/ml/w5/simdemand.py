"""SIM demand: 8 weeks of 15-min turning counts for J03-J08, generated from the 11 May survey profile.

Every number here is SIM (synthetic). Variability that real weeks would have, injected on purpose:
- weekday pattern (ASSUMED factors: Mon-Fri about 1.0, Saturday 0.9, Sunday 0.75),
- day-to-day level noise (lognormal, 5%) and slot-to-slot AR(1) noise per movement (8%),
- rain days (the whole corridor -15%), evening events near J03-J04 (+40%),
- incidents: one movement drops to 30-50% for an hour (labelled, for anomaly detection),
- surges: one movement +70% for 1-2 hours (labelled), closures: an approach counts 0 for an hour (labelled),
then Poisson sampling. The generator is seeded, so results are reproducible.
"""

from dataclasses import dataclass, field

import numpy as np

SLOTS = 96
DAYS = 56  # 8 weeks, day 0 = a Monday like 11 May 2026
DOW = np.array([1.0, 1.02, 1.01, 1.0, 1.04, 0.9, 0.75])  # ASSUMED weekday factors


@dataclass
class SimDemand:
    counts: np.ndarray  # (movements, DAYS * SLOTS) vehicles per 15 min
    expected: np.ndarray  # same shape: the mean before Poisson noise and injected anomalies
    keys: list[tuple[str, int]]  # (junction, movement) per row
    anomalies: list[dict] = field(default_factory=list)  # injected, with kind, rows, start, length


def generate(profile: np.ndarray, keys: list[tuple[str, int]], seed: int = 7, days: int = DAYS) -> SimDemand:
    """profile: (movements, 96) base counts (the 11 May survey). Returns SIM counts for `days` days."""
    rng = np.random.default_rng(seed)
    n = profile.shape[0]
    t = days * SLOTS
    level = np.exp(rng.normal(0, 0.05, days))
    base = np.concatenate([profile * DOW[d % 7] * level[d] for d in range(days)], axis=1)
    ar = np.zeros((n, t))
    eps = rng.normal(0, 0.08 * np.sqrt(1 - 0.7**2), (n, t))
    for k in range(1, t):
        ar[:, k] = 0.7 * ar[:, k - 1] + eps[:, k]
    mean = base * np.exp(ar)
    junction = np.array([k[0] for k in keys])
    for d in rng.choice(days, size=days // 7, replace=False):  # about one rain day a week
        mean[:, d * SLOTS : (d + 1) * SLOTS] *= 0.85
    near = np.isin(junction, ["J03", "J04"])
    for d in rng.choice(days, size=4, replace=False):  # evening events 17:00-21:00 (slots 36-51)
        mean[near, d * SLOTS + 36 : d * SLOTS + 52] *= 1.4
    expected = mean.copy()
    anomalies = []
    for kind, count in (("incident", 40), ("surge", 25), ("closure", 15)):
        for _ in range(count):
            d = int(rng.integers(0, days))
            start = d * SLOTS + int(rng.integers(8, 88))
            length = 4 if kind != "surge" else int(rng.integers(4, 9))
            if kind == "closure":  # every movement leaving one approach of one junction
                j = rng.choice(sorted(set(junction)))
                rows = [i for i, k in enumerate(keys) if k[0] == j][:3]
                mean[rows, start : start + length] = 0
            else:
                rows = [int(rng.integers(0, n))]
                f = rng.uniform(0.3, 0.5) if kind == "incident" else 1.7
                mean[rows, start : start + length] *= f
            anomalies.append({"kind": kind, "rows": rows, "start": start, "length": length})
    counts = rng.poisson(np.clip(mean, 0, None)).astype(float)
    return SimDemand(counts, expected, keys, anomalies)
