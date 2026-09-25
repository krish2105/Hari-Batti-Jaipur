"""Webster signal-timing maths and delay formulas (pure functions, no file access).

- webster_cycle / split_greens: same algorithm and rounding as services/sim/sim/timings.py,
  so the analytics and the simulator always agree on the assumed plan.
- uniform_delay: Webster's first (uniform arrival) delay term d1.
- incremental_delay: HCM 2000 random + overflow delay term d2 (pretimed signal).
- two_phase_plan: the assumed 2-phase, free-left plan built from survey PCU/h.

Nothing here controls a signal: these numbers are for analysis only.
"""

import math

from .data import ASSUMED_TIMING_LABEL


def webster_cycle(
    y_values: list[float], lost_time_s: float, min_c: float = 60, max_c: float = 180
) -> tuple[float, bool]:
    """Webster optimal cycle C0 = (1.5 L + 5) / (1 - Y), clamped to [min_c, max_c].

    Y is the sum of critical flow ratios. Returns (cycle, oversaturated).
    When Y >= 1 no fixed cycle can serve the demand: return (max_c, True).
    """
    y_sum = sum(y_values)
    if y_sum >= 1:
        return max_c, True
    c0 = (1.5 * lost_time_s + 5) / (1 - y_sum)
    return min(max(c0, min_c), max_c), False


def split_greens(y_values: list[float], total_green_s: float, min_green_s: float = 10) -> list[int]:
    """Share total green in proportion to each phase's flow ratio y, never below min green.

    Phases that would fall below the minimum get exactly the minimum; the rest is shared again.
    Rounded to whole seconds; the rounding error goes to the biggest phase so the sum is exact.
    (Copied rule-for-rule from the simulator so both give identical greens.)
    """
    n = len(y_values)
    fixed: set[int] = set()
    while True:
        free = [i for i in range(n) if i not in fixed]
        remaining = total_green_s - min_green_s * len(fixed)
        y_free = sum(y_values[i] for i in free) or 1.0
        greens = {i: remaining * y_values[i] / y_free for i in free}
        low = [i for i in free if greens[i] < min_green_s]
        if not low or len(fixed) + len(low) == n:
            break
        fixed.update(low)
    values = [float(min_green_s) if i in fixed else greens[i] for i in range(n)]
    rounded = [round(v) for v in values]
    rounded[rounded.index(max(rounded))] += round(total_green_s) - sum(rounded)
    return rounded


def uniform_delay(cycle_s: float, green_s: float, x: float) -> float:
    """Webster first term, seconds per vehicle: d1 = 0.5 C (1 - g/C)^2 / (1 - min(1, x) g/C).

    x is the degree of saturation; it is capped at 1 because above capacity the extra delay
    is carried by the incremental term instead.
    """
    g_ratio = green_s / cycle_s
    return 0.5 * cycle_s * (1 - g_ratio) ** 2 / (1 - min(1.0, x) * g_ratio)


def incremental_delay(x: float, capacity_veh_h: float, period_h: float = 0.25) -> float:
    """HCM 2000 incremental delay, seconds per vehicle (pretimed: k = 0.5, no upstream metering I = 1).

    d2 = 900 T [ (x - 1) + sqrt( (x - 1)^2 + 4 x / (c T) ) ]
    T = analysis period in hours, c = capacity in veh/h (or PCU/h). Grows fast once x > 1.
    """
    if capacity_veh_h <= 0:
        raise ValueError("capacity must be positive")
    t = period_h
    return 900 * t * ((x - 1) + math.sqrt((x - 1) ** 2 + 4 * x / (capacity_veh_h * t)))


def _flow_ratio(pcu_per_h: float, lanes: int, sat_flow: float) -> float:
    """y = flow / saturation flow of the lanes serving it."""
    return pcu_per_h / (lanes * sat_flow)


def two_phase_plan(
    approach_pcu: dict[str, dict[str, float]],
    main_approaches: tuple[str, str],
    lanes: dict[str, int],
    a: dict,
) -> dict:
    """Assumed 2-phase, free-left plan: main road together, then the two cross roads together.

    approach_pcu: {approach: {"L": pcu/h, "S": pcu/h, "R": pcu/h}} (survey peak hour).
    Left turns run free, so each approach's signal flow is S + R. A phase's flow ratio is the
    busier of its two approaches: (S + R) / (lanes x saturation flow).
    Lost time L = 2 phases x lost_time_per_phase_s. Total green = cycle - 2 (amber + all-red).
    `a` is the parsed services/sim/assumptions.toml.
    """
    sat = a["capacity"]["saturation_flow_pcu_per_lane_h"]
    t = a["timing"]
    main = tuple(main_approaches)
    cross = tuple(name for name in approach_pcu if name not in main)
    if len(cross) != 2:
        raise ValueError(f"Expected 2 cross approaches besides {main}, got {cross}")
    groups = [main, cross]

    def signal_flow(name: str) -> float:
        return approach_pcu[name]["S"] + approach_pcu[name]["R"]

    ys = [max(_flow_ratio(signal_flow(n), lanes[n], sat) for n in grp) for grp in groups]
    lost = a["capacity"]["lost_time_per_phase_s"] * len(groups)
    cycle, over = webster_cycle(ys, lost, t["webster_min_cycle_s"], t["webster_max_cycle_s"])
    cycle = round(cycle)
    intergreen = t["amber_s"] + t["all_red_s"]
    greens = split_greens(ys, cycle - intergreen * len(groups), t["min_green_s"])
    green_s = {name: g for grp, g in zip(groups, greens, strict=True) for name in grp}
    return {
        "cycle_s": int(cycle),
        "green_s": green_s,
        "Y": round(sum(ys), 3),
        "oversaturated": over,
        "label": ASSUMED_TIMING_LABEL,
    }
