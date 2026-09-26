"""Synthetic field-study runs (labelled SIM) to test the analysis pipeline before real drives.

NOT evidence: the effect in these runs comes from the model below, not from people. Model: one car
drives the corridor J08 -> J03 (plus 250 m before and after, removed later by the 200 m privacy trim).
Signals run their ASSUMED fixed plans (corridor.json) with main-road green starting at t = 0 mod cycle
(today's assumed zero offsets); the trip starts at a random time. Control: cruise at the driver's own
speed and stop at red. Advice: within 400 m of a signal, a GLOSA speed (15 km/h to limit - 5) that
arrives on green is followed 80% of the time; otherwise the driver behaves like control.
"""

import math
import random

from .geo import at_chainage, corridor

ACC, DEC = 1.5, 2.5  # m/s2
EXTRA_M = 250.0
DT = 0.5


def is_green(t: float, plan: dict) -> bool:
    return (t % plan["cycleS"]) < plan["mainGreenS"]


def next_green_window(t: float, plan: dict) -> tuple[float, float]:
    """Start and end (absolute s) of the current or next main-road green."""
    c, g = plan["cycleS"], plan["mainGreenS"]
    k = math.floor(t / c)
    start = k * c
    if t < start + g:
        return t, start + g
    return (k + 1) * c, (k + 1) * c + g


def run(arm: str, seed: int, limit_kmh: float | None = None) -> list[list[float]]:
    """One trip -> [[t, lat, lng, speed_kmh], ...] at 1 Hz with ~3 m GPS noise."""
    rnd = random.Random(seed)
    c = corridor()
    limit = limit_kmh or c["limit"]
    stops_at = [ch + EXTRA_M for ch in c["chainage"]]
    plans = [j["plan"] for j in c["junctions"]]
    end = c["chainage"][-1] + 2 * EXTRA_M
    cruise = min(limit - 5, rnd.gauss(38, 3)) / 3.6
    t0 = rnd.uniform(0, 600)
    t, s, v = t0, 0.0, cruise * 0.6
    comply = arm == "advice" and rnd.random() < 0.8
    out, next_emit = [], t0
    while s < end and t - t0 < 3600:
        ahead = [(k, x - s) for k, x in enumerate(stops_at) if x - s > -1]
        target = cruise
        if ahead:
            k, d = ahead[0]
            plan = plans[k]
            if comply and 0 < d <= 400:  # GLOSA: pick a speed that arrives on green
                lo, hi = 15 / 3.6, (limit - 5) / 3.6
                g0, g1 = next_green_window(t + d / hi, plan)
                arrive = max(t + d / hi, g0 + 1)
                want = d / max(arrive - t, 0.1)
                if lo <= want <= hi and arrive < g1:
                    target = want
            brake = v * v / (2 * DEC) + 3
            if not is_green(t + (d / max(v, 0.5)), plan) and d <= brake and not is_green(t, plan) and d > 0.5:
                target = 0.0 if d < 6 else min(target, math.sqrt(max(0.0, 2 * DEC * (d - 2))))
            if d <= 0.5 and not is_green(t, plan):
                target, v = 0.0, 0.0
        v = min(v + ACC * DT, target) if v < target else max(v - DEC * DT, target)
        s += v * DT
        t += DT
        if t >= next_emit:
            lat, lng = at_chainage(s - EXTRA_M)
            n = 3 / 111_000
            out.append(
                [
                    round(t, 1),
                    lat + rnd.gauss(0, n),
                    lng + rnd.gauss(0, n),
                    round(max(0.0, v * 3.6 + rnd.gauss(0, 0.5)), 1),
                ]
            )
            next_emit += 1.0
    return out


def cohort(n_runs: int = 20, seed: int = 20260926) -> list[dict]:
    """n runs from n/4 participants, 2 blocks each of (advice, control) in random order: SIM."""
    rnd = random.Random(seed)
    runs = []
    for p in range(n_runs // 4):
        for _block in range(2):
            arms = ["advice", "control"]
            rnd.shuffle(arms)
            for arm in arms:
                runs.append(
                    {
                        "participant": f"SIM-{p + 1}",
                        "arm": arm,
                        "direction": "east",
                        "points": run(arm, rnd.randrange(10**9)),
                    }
                )
    return runs
