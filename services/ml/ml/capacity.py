"""Capacity and v/c (degree of saturation) per junction approach at the AM and PM peak hours.

Inputs (all real files, nothing invented):
  flows   -> PM: data/processed/pm_peak_approach_turns.csv (PCU/h in each junction's PM peak hour)
             AM: data/processed/tmc_clean.csv, the four 15-min slots of the junction's AM peak hour
                 (am_peak_start in junction_day_summary.csv). Local-only file: skipped if missing.
  lanes   -> registry lanes_per_approach, else assumptions.toml (marked ASSUMED)
  timing  -> FIELD rows in data/signal_timings.csv, else the assumed 2-phase free-left plan
             built from that day's PM-peak survey PCU (one fixed plan used for AM and PM).

capacity = saturation flow x lanes x g / C;  v/c = flow / capacity;  flag when v/c > 0.9.
Under the assumed plan left turns run free, so the flow counted is S + R (the signal-served part).
"""

import warnings

from . import data
from .metrics import ApproachHour
from .webster import two_phase_plan

VC_FLAG_LIMIT = 0.9


def _field_timing(rows: list[dict[str, str]], approach_names: tuple[str, ...]) -> dict:
    """Green per approach and cycle from real stopwatch rows (first time window listed).

    An approach's green is the sum of the greens of every phase that serves its straight movement
    (or lists it with no turns). Cycle = the cycle_s column when given, else the sum of all phases.
    """
    window = rows[0]["time_window"]
    chosen = [r for r in rows if r["time_window"] == window]
    green = dict.fromkeys(approach_names, 0)
    total = 0.0
    for r in chosen:
        g = float(r["green_s"])
        total += g + float(r["amber_s"] or 0) + float(r["all_red_s"] or 0)
        for part in r["approaches_served"].split(";"):
            name, _, turns = part.partition("(")
            name = name.strip()
            served = [t.strip() for t in turns.rstrip(") ").split("+")] if turns else ["S"]
            if name in green and "S" in served:
                green[name] += g
    cycle_col = (chosen[0].get("cycle_s") or "").strip()
    return {
        "cycle_s": float(cycle_col) if cycle_col else total,
        "green_s": green,
        "label": data.FIELD_TIMING_LABEL,
        "source": "FIELD",
        "oversaturated": None,
        "Y": None,
        "time_window": window,
    }


def junction_timing(junction_id: str, date: str = "2026-05-11") -> dict:
    """Timing used for analysis: FIELD rows win, else the assumed 2-phase plan for that date.

    Returns {cycle_s, green_s {approach: s}, label, source ("FIELD"/"ASSUMED"), oversaturated, Y}.
    """
    field = data.load_field_timings()
    if junction_id in field:
        return _field_timing(field[junction_id], data.approaches(junction_id))
    pm = data.load_pm_peak(date).get(junction_id)
    if pm is None:
        raise KeyError(f"No PM-peak survey counts for {junction_id} on {date}")
    lanes, _ = data.lanes_for(junction_id)
    plan = two_phase_plan(pm, data.main_approaches(junction_id), lanes, data.load_assumptions())
    return plan | {"source": "ASSUMED"}


def _am_flows(date: str, turns: tuple[str, ...]) -> dict[str, dict[str, float]]:
    """AM-peak-hour PCU/h per junction -> approach: sum of the 4 slots from am_peak_start."""
    per_slot = data.slot_approach_pcu(date, turns)
    out: dict[str, dict[str, float]] = {}
    for (jid, d), summary in data.load_day_summary().items():
        if d != date:
            continue
        first = data.slot_of(summary["am_peak_start"])
        slots = range(first, first + 4)
        out[jid] = {
            appr: sum(per_slot.get((jid, appr, s), 0.0) for s in slots) for appr in data.approaches(jid)
        }
    return out


def _row(jid: str, appr: str, period: str, hour_start: str, flow: float, timing: dict) -> dict:
    """One v/c table row for one approach and one peak hour."""
    lanes, lane_src = data.lanes_for(jid)
    sat = data.load_assumptions()["capacity"]["saturation_flow_pcu_per_lane_h"]
    green = timing["green_s"].get(appr, 0)
    cap = sat * lanes[appr] * green / timing["cycle_s"]
    vc = flow / cap if cap > 0 else None
    return {
        "junction_id": jid,
        "approach": appr,
        "period": period,
        "hour_start": hour_start,
        "flow_pcu_h": round(flow, 1),
        "turns_counted": "S+R" if timing["source"] == "ASSUMED" else "L+S+R",
        "lanes": lanes[appr],
        "lanes_source": lane_src[appr],
        "green_s": green,
        "cycle_s": timing["cycle_s"],
        "timing_label": timing["label"],
        "timing_source": timing["source"],
        "capacity_pcu_h": round(cap, 1),
        "vc": None if vc is None else round(vc, 3),
        "flag": "no green found" if vc is None else ("over 0.9" if vc > VC_FLAG_LIMIT else ""),
        "data_label": data.SURVEY_LABEL,
    }


def vc_table(date: str = "2026-05-11") -> list[dict]:
    """v/c per junction approach at the AM and PM peak hours of one survey date.

    Rows: junction_id, approach, period ("AM"/"PM"), hour_start, flow_pcu_h, lanes, lanes_source,
    green_s, cycle_s, timing_label, capacity_pcu_h, vc, flag ("over 0.9" when v/c > 0.9).
    If tmc_clean.csv is missing, only PM rows are returned and a warning explains why.
    """
    pm = data.load_pm_peak(date)
    summary = data.load_day_summary()
    have_am = data.TMC_CSV.exists()
    if have_am:
        am_by_turns = {"S+R": _am_flows(date, ("S", "R")), "L+S+R": _am_flows(date, data.TURNS)}
    else:
        warnings.warn(f"AM rows skipped: {data.TMC_MISSING_MSG}", stacklevel=2)
    rows: list[dict] = []
    for jid in data.junction_ids():
        if jid not in pm:
            continue
        timing = junction_timing(jid, date)
        # Assumed plan: left turns run free, so only S + R need the signal. FIELD: all turns.
        turns = ("S", "R") if timing["source"] == "ASSUMED" else data.TURNS
        day = summary[(jid, date)]
        if have_am:
            am = am_by_turns["+".join(turns)][jid]
            for appr in data.approaches(jid):
                rows.append(_row(jid, appr, "AM", day["am_peak_start"], am[appr], timing))
        for appr in data.approaches(jid):
            flow = sum(pm[jid][appr][t] for t in turns)
            rows.append(_row(jid, appr, "PM", day["pm_peak_start"], flow, timing))
    return rows


def approach_hours(date: str = "2026-05-11") -> list[ApproachHour]:
    """Every junction approach x clock hour of one survey day, ready for ml.metrics.

    Flow = S + R PCU/h from tmc_clean (left turns run free under the assumed plan; all turns under
    a FIELD plan). Link length = assumptions geometry.link_spacing_m (ASSUMED). Pedestrian inputs
    are unknown, so they stay None. Needs tmc_clean.csv (raises FileNotFoundError if missing).
    """
    a = data.load_assumptions()
    sat = a["capacity"]["saturation_flow_pcu_per_lane_h"]
    link = float(a["geometry"]["link_spacing_m"])
    flows_sr = data.hourly_approach_pcu(date, ("S", "R"))
    flows_all = data.hourly_approach_pcu(date)
    out: list[ApproachHour] = []
    for jid in data.junction_ids():
        if (jid, date) not in data.load_day_summary():
            continue
        timing = junction_timing(jid, date)
        flows = flows_sr if timing["source"] == "ASSUMED" else flows_all
        lanes, _ = data.lanes_for(jid)
        for appr in data.approaches(jid):
            for hour in range(24):
                out.append(
                    ApproachHour(
                        junction_id=jid,
                        approach=appr,
                        hour=hour,
                        flow_pcu_h=flows.get((jid, appr, hour), 0.0),
                        lanes=lanes[appr],
                        green_s=float(timing["green_s"][appr]),
                        cycle_s=float(timing["cycle_s"]),
                        sat_flow=sat,
                        link_length_m=link,
                    )
                )
    return out
