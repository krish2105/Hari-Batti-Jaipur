"""Field-study rules (P8 W14), pure and unit-tested: trace trimming, randomisation and validation.

- Privacy: the first and last TRIM_M metres of every trace are removed before storage, so no home or
  work address can be read from it; traces are deleted after 30 days; participants are random IDs.
- Randomisation: permuted blocks of two per participant (one advice run and one control run in random
  order), so every participant contributes to both arms and the arms stay balanced.
"""

import math
import secrets
from itertools import pairwise

TRIM_M = 200.0
MAX_POINTS = 4 * 3600  # 4 hours at 1 Hz
ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I


def new_participant_id() -> str:
    return "P-" + "".join(secrets.choice(ID_ALPHABET) for _ in range(6))


def new_invite_code() -> str:
    return "".join(secrets.choice(ID_ALPHABET) for _ in range(8))


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def trim(points: list[list[float]], trim_m: float = TRIM_M) -> list[list[float]]:
    """Drop the points within `trim_m` metres (along the path) of the start and of the end."""
    if len(points) < 2:
        return []
    cum = [0.0]
    for p, q in pairwise(points):
        cum.append(cum[-1] + haversine_m((p[1], p[2]), (q[1], q[2])))
    total = cum[-1]
    if total <= 2 * trim_m:
        return []
    return [p for p, d in zip(points, cum, strict=True) if trim_m <= d <= total - trim_m]


def next_arm(previous: list[str], rnd: secrets.SystemRandom | None = None) -> str:
    """Permuted blocks of two: start each block at random, finish it with the other arm."""
    rnd = rnd or secrets.SystemRandom()
    if len(previous) % 2 == 1:
        return "control" if previous[-1] == "advice" else "advice"
    return rnd.choice(["advice", "control"])


def validate(points: list[list[float]]) -> str | None:
    """A reason the trace is unusable, or None."""
    if not 30 <= len(points) <= MAX_POINTS:
        return f"a run needs 30 to {MAX_POINTS} points (got {len(points)})"
    for p in points:
        if len(p) != 4 or not (-90 <= p[1] <= 90 and -180 <= p[2] <= 180 and 0 <= p[3] <= 200):
            return "every point must be [t, lat, lng, speed_kmh] with a valid position and speed"
    ts = [p[0] for p in points]
    if any(b <= a for a, b in pairwise(ts)):
        return "timestamps must increase"
    return None
