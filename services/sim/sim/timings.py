"""Signal timing plans for each junction.

Priority:
  1. FIELD  — real stopwatch rows in data/signal_timings.csv (rows marked EXAMPLE are ignored)
  2. ASSUMED — one of three labelled plans (none of them is a recommendation):
       "demand2"  Assumed timing – demand-proportional (2-phase, free left)   <- default
       "webster4" Assumed timing – demand-proportional (approach-wise, Webster)
       "even"     Assumed timing – even split (approach-wise 4 x 25 s)
Plans here are pure data: SUMO state strings are made from them in build.py.
"""

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .config import PM_PEAK_CSV, TIMINGS_CSV, Assumptions

PLAN_LABELS = {
    "demand2": "Assumed timing – demand-proportional (2-phase, free left)",
    "webster4": "Assumed timing – demand-proportional (approach-wise, Webster)",
    "even": "Assumed timing – even split",
    "field": "Field timing (stopwatch, data/signal_timings.csv)",
}
TURNS = ("L", "S", "R")


@dataclass(frozen=True)
class Phase:
    """One step of the signal program.

    kind: "green", "amber" or "allred".
    moves: (side, turn) -> "G" (protected green), "g" (permitted: gives way), "y" (amber).
    Any (side, turn) not listed is red.
    """

    kind: str
    duration_s: int
    moves: dict[tuple[str, str], str] = field(default_factory=dict)


@dataclass(frozen=True)
class Plan:
    junction_id: str
    plan_id: str
    label: str
    timing: str  # "ASSUMED" or "FIELD"
    phasing: str  # "2PHASE_FREE_LEFT", "APPROACH_WISE" or "FIELD"
    phases: tuple[Phase, ...]
    webster_y: float | None = None
    oversaturated: bool = False
    notes: tuple[str, ...] = ()

    @property
    def cycle_s(self) -> int:
        return sum(p.duration_s for p in self.phases)


# ---------------------------------------------------------------- Webster maths (pure)


def webster_cycle(
    y_values: list[float], lost_time_s: float, min_c: float, max_c: float
) -> tuple[float, bool]:
    """Webster optimal cycle C0 = (1.5 L + 5) / (1 - Y), clamped to [min_c, max_c].

    Returns (cycle, oversaturated). When Y >= 1 no cycle works: return max_c, oversaturated=True.
    """
    y_sum = sum(y_values)
    if y_sum >= 1:
        return max_c, True
    c0 = (1.5 * lost_time_s + 5) / (1 - y_sum)
    return min(max(c0, min_c), max_c), False


def split_greens(y_values: list[float], total_green_s: float, min_green_s: float) -> list[int]:
    """Share total green in proportion to each phase's flow ratio y, never below min green.

    Phases that would fall below the minimum get exactly the minimum; the rest is shared again.
    Rounded to whole seconds; rounding error goes to the biggest phase so the sum is exact.
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


def flow_ratio(pcu_per_h: float, lanes: int, sat_flow: float) -> float:
    """y = flow / saturation flow of the lanes serving it."""
    return pcu_per_h / (lanes * sat_flow)


# ---------------------------------------------------------------- inputs


def load_pm_peak(date: str, path: Path = PM_PEAK_CSV) -> dict[str, dict[str, dict[str, float]]]:
    """PM-peak PCU/h per junction -> approach -> turn (survey, from data/processed)."""
    out: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["survey_date"] == date:
                out[r["junction_id"]][r["from_approach"]] = {t: float(r[t]) for t in TURNS}
    return dict(out)


def load_field_rows(path: Path = TIMINGS_CSV) -> dict[str, list[dict]]:
    """Real stopwatch rows grouped by junction. Rows whose notes contain EXAMPLE are dropped."""
    rows: dict[str, list[dict]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if "EXAMPLE" in (r.get("notes") or "").upper():
                continue
            if (r.get("junction_id") or "").strip():
                rows[r["junction_id"].strip()].append(r)
    return dict(rows)


# ---------------------------------------------------------------- plan builders


def _intergreen(moves_green: dict[tuple[str, str], str], a: Assumptions, keep: set) -> list[Phase]:
    """Amber then all-red after a green. Movements in `keep` (free lefts) stay green."""
    t = a["timing"]
    amber = {k: ("G" if k in keep else "y") for k in moves_green}
    amber.update({k: "G" for k in keep})
    allred = {k: "G" for k in keep}
    return [Phase("amber", int(t["amber_s"]), amber), Phase("allred", int(t["all_red_s"]), allred)]


def plan_two_phase(
    junction_id: str,
    side_of: dict[str, str],
    lanes: dict[str, int],
    pm_peak: dict[str, dict[str, float]],
    a: Assumptions,
) -> Plan:
    """2-phase, free left: main road (W+E) together, then cross roads (N+S) together.

    Left turns are free (always green). Right turns are permitted ("g": give way to oncoming).
    Phase flow ratio = the busier of its two approaches, (S + R) PCU/h over its lanes.
    """
    sat = a["capacity"]["saturation_flow_pcu_per_lane_h"]
    t = a["timing"]
    groups = [("W", "E"), ("N", "S")]
    at = {side: name for name, side in side_of.items()}
    ys = [
        max(flow_ratio(pm_peak[at[s]]["S"] + pm_peak[at[s]]["R"], lanes[at[s]], sat) for s in grp)
        for grp in groups
    ]
    lost = a["capacity"]["lost_time_per_phase_s"] * len(groups)
    cycle, over = webster_cycle(ys, lost, t["webster_min_cycle_s"], t["webster_max_cycle_s"])
    cycle = round(cycle)
    inter = t["amber_s"] + t["all_red_s"]
    greens = split_greens(ys, cycle - inter * len(groups), t["min_green_s"])
    free_left = {(s, "L") for s in ("W", "N", "E", "S")}
    phases: list[Phase] = []
    for grp, g in zip(groups, greens):
        moves = {(s, "S"): "G" for s in grp} | {(s, "R"): "g" for s in grp}
        phases.append(Phase("green", g, moves | {k: "G" for k in free_left}))
        phases += _intergreen(moves, a, free_left)
    return Plan(
        junction_id,
        "demand2",
        PLAN_LABELS["demand2"],
        "ASSUMED",
        "2PHASE_FREE_LEFT",
        tuple(phases),
        round(sum(ys), 3),
        over,
        ("oversaturated: demand exceeds 2-phase capacity",) if over else (),
    )


def _approach_wise(
    junction_id: str, plan_id: str, greens: list[int], ys: list[float] | None, over: bool, a: Assumptions
) -> Plan:
    """One green per approach in clockwise order W, N, E, S; all its turns protected."""
    phases: list[Phase] = []
    for side, g in zip(("W", "N", "E", "S"), greens):
        moves = {(side, turn): "G" for turn in TURNS}
        phases.append(Phase("green", g, moves))
        phases += _intergreen(moves, a, set())
    notes = ("oversaturated: demand exceeds 4-stage capacity",) if over else ()
    return Plan(
        junction_id,
        plan_id,
        PLAN_LABELS[plan_id],
        "ASSUMED",
        "APPROACH_WISE",
        tuple(phases),
        round(sum(ys), 3) if ys else None,
        over,
        notes,
    )


def plan_even(junction_id: str, a: Assumptions) -> Plan:
    """Status-quo guess: 4 x (25 s green + 3 s amber + 2 s all-red) = 120 s."""
    return _approach_wise(junction_id, "even", [int(a["timing"]["even_split_green_s"])] * 4, None, False, a)


def approach_wise_y(
    side_of: dict[str, str], lanes: dict[str, int], pm_peak: dict[str, dict[str, float]], a: Assumptions
) -> list[float]:
    """Flow ratio per approach (W, N, E, S) when each approach runs alone (all turns)."""
    sat = a["capacity"]["saturation_flow_pcu_per_lane_h"]
    at = {side: name for name, side in side_of.items()}
    return [flow_ratio(sum(pm_peak[at[s]].values()), lanes[at[s]], sat) for s in ("W", "N", "E", "S")]


def plan_webster4(
    junction_id: str,
    side_of: dict[str, str],
    lanes: dict[str, int],
    pm_peak: dict[str, dict[str, float]],
    a: Assumptions,
) -> Plan:
    """Approach-wise Webster. With this corridor's demand Y > 1, so it is capped at 180 s."""
    t = a["timing"]
    ys = approach_wise_y(side_of, lanes, pm_peak, a)
    lost = a["capacity"]["lost_time_per_phase_s"] * 4
    cycle, over = webster_cycle(ys, lost, t["webster_min_cycle_s"], t["webster_max_cycle_s"])
    cycle = round(cycle)
    greens = split_greens(ys, cycle - (t["amber_s"] + t["all_red_s"]) * 4, t["min_green_s"])
    return _approach_wise(junction_id, "webster4", greens, ys, over, a)


def plan_field(junction_id: str, rows: list[dict], side_of: dict[str, str], a: Assumptions) -> Plan:
    """Build a plan from stopwatch rows.

    approaches_served format: "Approach Name (S+L); Other Approach (R)". Turns default to all.
    If several time windows exist, the first window listed is used (noted on the plan).
    """
    windows = list(dict.fromkeys(r["time_window"] for r in rows))
    chosen = [r for r in rows if r["time_window"] == windows[0]]
    phases: list[Phase] = []
    for r in sorted(chosen, key=lambda r: int(r["phase_no"])):
        moves: dict[tuple[str, str], str] = {}
        for part in r["approaches_served"].split(";"):
            name, _, turns = part.partition("(")
            name = name.strip()
            if name not in side_of:
                raise ValueError(f"{junction_id}: unknown approach {name!r} in signal_timings.csv")
            for turn in turns.rstrip(") ").split("+") if turns else TURNS:
                moves[(side_of[name], turn.strip())] = "G"
        phases.append(Phase("green", int(float(r["green_s"])), moves))
        phases.append(Phase("amber", int(float(r["amber_s"] or 0)), {k: "y" for k in moves}))
        if float(r["all_red_s"] or 0) > 0:
            phases.append(Phase("allred", int(float(r["all_red_s"])), {}))
    notes = (f"time window {windows[0]} used of {windows}",) if len(windows) > 1 else ()
    return Plan(junction_id, "field", PLAN_LABELS["field"], "FIELD", "FIELD", tuple(phases), notes=notes)


def choose_plan(
    plan_id: str,
    junction_id: str,
    side_of: dict[str, str],
    lanes: dict[str, int],
    pm_peak: dict[str, dict[str, float]],
    field_rows: dict[str, list[dict]],
    a: Assumptions,
) -> Plan:
    """FIELD rows always win; otherwise the requested assumed plan."""
    if junction_id in field_rows:
        return plan_field(junction_id, field_rows[junction_id], side_of, a)
    if plan_id == "demand2":
        return plan_two_phase(junction_id, side_of, lanes, pm_peak, a)
    if plan_id == "webster4":
        return plan_webster4(junction_id, side_of, lanes, pm_peak, a)
    if plan_id == "even":
        return plan_even(junction_id, a)
    raise ValueError(f"Unknown plan {plan_id!r}; use demand2, webster4 or even")


def webster_y_table(side_of: dict[str, str], lanes: dict[str, int], pm_peak, a: Assumptions) -> dict:
    """Y under 2-phase and approach-wise phasing, for the calibration report."""
    two = plan_two_phase("-", side_of, lanes, pm_peak, a).webster_y
    four = round(sum(approach_wise_y(side_of, lanes, pm_peak, a)), 3)
    return {"two_phase_y": two, "approach_wise_y": four}
