"""Green wave for the main road J08 -> J03 (and back): common cycle + offsets that maximise the
green bandwidth in both directions at a chosen progression speed.

Bandwidth: the longest stretch of time (seconds per cycle) during which a car driving at the
progression speed passes every junction on green. Offsets say when each junction's main-road
green starts (seconds into the common cycle) — the same meaning as the dashboard's time-space
diagram and SUMO's tlLogic offset. Computed on the ASSUMED 500 m spacing: SIM / ASSUMED.
"""

import math
import random
from dataclasses import dataclass, replace

STEP_S = 0.5  # time resolution of the bandwidth search


@dataclass(frozen=True)
class Junction:
    id: str
    x: float  # metres from the west end (J08)
    green: float  # main-road green (s)
    offset: float  # main-road green start (s into the cycle)


def _open_times(j: Junction, cycle: float, shift: float) -> list[bool]:
    """For each sample t of one cycle: is a car that passes the reference at t green at j?"""
    n = round(cycle / STEP_S)
    return [((k * STEP_S + shift - j.offset) % cycle) < j.green for k in range(n)]


def bandwidth(js: list[Junction], cycle: float, speed_ms: float, direction: str) -> float:
    """Width (s) of the widest band of green through every junction, eastbound or westbound."""
    far = max(j.x for j in js)
    ok = None
    for j in js:
        travel = (j.x if direction == "east" else far - j.x) / speed_ms
        row = _open_times(j, cycle, travel)
        ok = row if ok is None else [a and b for a, b in zip(ok, row, strict=True)]
    if ok is None or not any(ok):
        return 0.0
    if all(ok):
        return cycle
    # longest circular run of True
    best = run = 0
    for v in ok + ok:
        run = run + 1 if v else 0
        best = max(best, run)
    return min(best, len(ok)) * STEP_S


def total(js: list[Junction], cycle: float, speed_ms: float) -> float:
    """Search objective: both bands, plus the narrower one again so neither direction is sacrificed."""
    e, w = bandwidth(js, cycle, speed_ms, "east"), bandwidth(js, cycle, speed_ms, "west")
    return e + w + min(e, w)


def optimise_offsets(
    js: list[Junction], cycle: float, speed_ms: float, restarts: int = 20, seed: int = 0
) -> list[Junction]:
    """Coordinate search over 1-s offsets (first junction fixed at 0), best of several random starts."""
    rng = random.Random(seed)
    grid = list(range(int(cycle)))
    best, best_score = js, -1.0
    for r in range(restarts):
        cur = [
            replace(j, offset=0.0 if i == 0 else float(rng.choice(grid) if r else j.offset))
            for i, j in enumerate(js)
        ]
        score = total(cur, cycle, speed_ms)
        improved = True
        while improved:
            improved = False
            for i in range(1, len(cur)):
                for o in grid:
                    trial = cur[:i] + [replace(cur[i], offset=float(o))] + cur[i + 1 :]
                    s = total(trial, cycle, speed_ms)
                    if s > score + 1e-9:
                        cur, score, improved = trial, s, True
        if score > best_score:
            best, best_score = cur, score
    return best


def common_plan(
    plans: dict[str, tuple[int, int, int]], intergreen_s: int
) -> tuple[int, dict[str, tuple[int, int]]]:
    """Common cycle (the longest junction cycle, rounded up to 5 s) and each junction's
    (main, cross) greens rescaled to it with the same main-road share of green."""
    cycle = int(math.ceil(max(c for c, _, _ in plans.values()) / 5) * 5)
    greens = {}
    for jid, (_c, main, cross) in plans.items():
        g = cycle - intergreen_s
        m = round(g * main / (main + cross))
        greens[jid] = (m, g - m)
    return cycle, greens


def best_common_plan(
    plans: dict[str, tuple[int, int, int]],
    xs: dict[str, float],
    intergreen_s: int,
    speed_ms: float,
    max_cycle: int = 120,
    restarts: int = 6,
) -> tuple[int, list[Junction]]:
    """Try every common cycle from the longest junction cycle up to max_cycle (5-s steps), rescale the
    greens, optimise offsets, and keep the cycle with the largest two-way band as a share of the cycle."""
    first, _ = common_plan(plans, intergreen_s)
    best: tuple[float, int, list[Junction]] | None = None
    for cycle in range(first, max(first, max_cycle) + 1, 5):
        _, greens = common_plan({j: (cycle, *plans[j][1:]) for j in plans}, intergreen_s)
        js = [Junction(j, xs[j], greens[j][0], 0.0) for j in plans]
        js = optimise_offsets(js, cycle, speed_ms, restarts=restarts, seed=cycle)
        score = total(js, cycle, speed_ms) / cycle
        if best is None or score > best[0] + 1e-9:
            best = (score, cycle, js)
    assert best is not None
    return best[1], best[2]
