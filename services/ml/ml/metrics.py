"""The five Junction Health metrics and the 0-100 Health Score (docs/02-dashboard.md).

All functions are pure: give them one approach-hour (flow, lanes, green, cycle ...) and they
return a number. Flows are PCU/h; times are seconds.

  red wait (s)          average delay per vehicle = Webster d1 + HCM 2000 d2
  cycles-to-clear       max(1, x): rough average number of cycles a queued vehicle needs
  starvation ratio      green given / green needed (needed = green that would give x = 0.9)
  ped clearance ratio   pedestrian green / (crossing width / 1.0 m/s walking speed)
  spillback minutes     minutes in the hour the queue is longer than the upstream link

Health = 100 - (30 s_wait + 25 s_clear + 20 s_starve + 15 s_ped + 10 s_spill), each s in [0, 1].
"""

from dataclasses import dataclass

from .webster import incremental_delay, uniform_delay

PCU_LENGTH_M = 6.5  # road space one queued PCU takes (car length + gap)
WALK_SPEED_M_S = 1.0  # design walking speed for pedestrian clearance
TARGET_X = 0.9  # starvation: green needed is the green that would run the approach at x = 0.9
STARVATION_CAP = 10.0  # empty approach -> "plenty of green", kept finite so it is JSON-safe
WEIGHTS = {"s_wait": 30, "s_clear": 25, "s_starve": 20, "s_ped": 15, "s_spill": 10}


@dataclass(frozen=True)
class ApproachHour:
    """One approach during one hour, everything the metrics need."""

    junction_id: str
    approach: str
    hour: int
    flow_pcu_h: float
    lanes: int
    green_s: float
    cycle_s: float
    sat_flow: float = 1800
    crossing_width_m: float | None = None
    ped_green_s: float | None = None
    link_length_m: float | None = None


def capacity_pcu_h(a: ApproachHour) -> float:
    """Capacity = saturation flow x lanes x g / C (PCU/h)."""
    if a.green_s <= 0 or a.cycle_s <= 0:
        raise ValueError(f"{a.junction_id} {a.approach}: green and cycle must be positive")
    return a.sat_flow * a.lanes * a.green_s / a.cycle_s


def degree_of_saturation(a: ApproachHour) -> float:
    """x = flow / capacity (also called v/c)."""
    return a.flow_pcu_h / capacity_pcu_h(a)


def red_wait_s(a: ApproachHour) -> float:
    """Average red wait = average control delay per vehicle, d1 + d2 (seconds)."""
    x = degree_of_saturation(a)
    return uniform_delay(a.cycle_s, a.green_s, x) + incremental_delay(x, capacity_pcu_h(a))


def cycles_to_clear(a: ApproachHour) -> float:
    """Approximate average signal cycles a queued vehicle needs to get through: max(1, x).

    Below capacity every vehicle clears in the first green (1 cycle); above capacity the
    queue carries over, so on average it takes about x cycles. An approximation, not a count.
    """
    return max(1.0, degree_of_saturation(a))


def starvation_ratio(a: ApproachHour) -> float:
    """Green given / green needed. Green needed = flow x C / (sat x lanes) / 0.9.

    That is the effective green that would run the approach at x = 0.9. Below 0.8 = starved.
    An approach with no flow returns STARVATION_CAP (10) so the value stays finite.
    """
    needed = a.flow_pcu_h * a.cycle_s / (a.sat_flow * a.lanes) / TARGET_X
    if needed <= 0:
        return STARVATION_CAP
    return min(a.green_s / needed, STARVATION_CAP)


def ped_clearance_ratio(a: ApproachHour) -> float | None:
    """Pedestrian green / time needed to cross (width / 1.0 m/s). None when inputs are unknown."""
    if a.ped_green_s is None or a.crossing_width_m is None:
        return None
    return a.ped_green_s / (a.crossing_width_m / WALK_SPEED_M_S)


def spillback_minutes(a: ApproachHour) -> float:
    """Minutes in the hour the queue (per lane, 6.5 m per PCU) is longer than the link.

    x <= 1: the longest queue is what arrives during red, flow x (C - g) / 3600 PCU, spread over
            the lanes. If that is longer than the link it spills back every cycle -> 60, else 0.
    x > 1:  on top of the red queue a leftover queue grows by (flow - capacity) / 60 PCU per
            minute. Spill minutes = 60 - (minute when the queue first passes the link), in [0, 60].
    Unknown link length -> 0.
    """
    if a.link_length_m is None:
        return 0.0
    red_queue_pcu = a.flow_pcu_h * (a.cycle_s - a.green_s) / 3600
    link_pcu = a.link_length_m * a.lanes / PCU_LENGTH_M  # PCU that fit on the link (all lanes)
    x = degree_of_saturation(a)
    if x <= 1:
        return 60.0 if red_queue_pcu > link_pcu else 0.0
    growth_per_min = (a.flow_pcu_h - capacity_pcu_h(a)) / 60
    first_minute = (link_pcu - red_queue_pcu) / growth_per_min
    return min(60.0, max(0.0, 60.0 - first_minute))


# ---------------------------------------------------------------- score


def _scale(value: float, good: float, bad: float) -> float:
    """0 at `good`, 1 at `bad`, straight line in between, clamped to [0, 1] (works both directions)."""
    s = (value - good) / (bad - good)
    return min(1.0, max(0.0, s))


def penalties(metrics: dict) -> dict:
    """Turn the five metrics into 0-1 penalties.

    s_wait   0 at <= 30 s    -> 1 at >= 60 s
    s_clear  0 at <= 1.0     -> 1 at >= 1.2
    s_starve 0 at >= 1.0     -> 1 at <= 0.8
    s_ped    0 at >= 1.2     -> 1 at <= 1.0   (None when the ped ratio is unknown)
    s_spill  0 at 0 min      -> 1 at >= 15 min
    """
    ped = metrics.get("ped_ratio")
    return {
        "s_wait": _scale(metrics["red_wait_s"], 30, 60),
        "s_clear": _scale(metrics["cycles_to_clear"], 1.0, 1.2),
        "s_starve": _scale(metrics["starvation"], 1.0, 0.8),
        "s_ped": None if ped is None else _scale(ped, 1.2, 1.0),
        "s_spill": _scale(metrics["spill_min"], 0, 15),
    }


def health_score(metrics: dict) -> float:
    """Health = 100 - (30 s_wait + 25 s_clear + 20 s_starve + 15 s_ped + 10 s_spill), 1 decimal.

    Accepts either the metrics dict (red_wait_s, cycles_to_clear, starvation, ped_ratio,
    spill_min) or a ready penalties dict (s_wait ...). When s_ped is None its weight is dropped
    and the rest rescaled: 100 - 100 x sum(w s) / sum(w).
    """
    s = metrics if "s_wait" in metrics else penalties(metrics)
    used = {k: w for k, w in WEIGHTS.items() if s.get(k) is not None}
    weighted = sum(w * s[k] for k, w in used.items())
    return round(100 - 100 * weighted / sum(used.values()), 1)


def approach_metrics(a: ApproachHour) -> dict:
    """All five metrics (plus x and health) for one approach-hour."""
    m = {
        "junction_id": a.junction_id,
        "approach": a.approach,
        "hour": a.hour,
        "flow_pcu_h": a.flow_pcu_h,
        "x": degree_of_saturation(a),
        "red_wait_s": red_wait_s(a),
        "cycles_to_clear": cycles_to_clear(a),
        "starvation": starvation_ratio(a),
        "ped_ratio": ped_clearance_ratio(a),
        "spill_min": spillback_minutes(a),
    }
    m["health"] = health_score(m)
    return m


def junction_metrics(approach_hours: list[ApproachHour]) -> dict:
    """Roll approaches up to one junction: flow-weighted means of red wait, cycles-to-clear and
    starvation (plus the worst approach's starvation), worst pedestrian ratio, worst spillback.

    If every approach has zero flow, plain (unweighted) means are used instead.
    """
    if not approach_hours:
        raise ValueError("junction_metrics needs at least one ApproachHour")
    per = [approach_metrics(a) for a in approach_hours]
    total = sum(m["flow_pcu_h"] for m in per)
    weights = [m["flow_pcu_h"] / total for m in per] if total > 0 else [1 / len(per)] * len(per)

    def wmean(key: str) -> float:
        return sum(w * m[key] for w, m in zip(weights, per, strict=True))

    peds = [m["ped_ratio"] for m in per if m["ped_ratio"] is not None]
    out = {
        "red_wait_s": wmean("red_wait_s"),
        "cycles_to_clear": wmean("cycles_to_clear"),
        "starvation": wmean("starvation"),
        "starvation_min": min(m["starvation"] for m in per),
        "ped_ratio": min(peds) if peds else None,
        "spill_min": max(m["spill_min"] for m in per),
    }
    out["health"] = health_score(out)
    out["approaches"] = per
    return out
