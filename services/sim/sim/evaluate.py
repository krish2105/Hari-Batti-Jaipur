"""Fast scoring of a build on a few time windows (used by W1 diagnostics and Optuna calibration).

Each window runs as its own headless SUMO process (in parallel): warm-up, then N scored hours.
Scores: share of movement-hours with GEH < 5 against a survey date, unserved demand (vehicles
still waiting to enter at the end), teleports. Calibrate on 11 May; 12 May is only ever reported.
"""

import json
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import config
from .build import load_manifest
from .calibrate import GEH_OK, geh, via_lane_map
from .demand import load_day
from .stream import sumo_command
from .sumo_env import sumolib

# survey hour index (0 = 08:00): 09-10 AM peak, 13-14 midday, 18-19 PM peak
DEFAULT_WINDOWS = ((1, 1), (5, 1), (10, 1))


def run_window(
    build_dir: Path, start_h: int, hours: int, warmup_min: int = 15, plan: str = "demand2"
) -> dict:
    """One SUMO run: [start - warm-up, start + hours]. Returns simulated turn counts per hour."""
    begin_scored = start_h * 3600
    begin = max(0, begin_scored - warmup_min * 60)
    end = begin_scored + hours * 3600
    with tempfile.TemporaryDirectory(prefix="w1-eval-") as tmp:
        work = Path(tmp)
        add = work / "meas.add.xml"
        add.write_text(
            f'<additional><laneData id="turns" begin="{begin_scored}" end="{end}" period="3600" '
            f'file="{work / "turns.xml"}" withInternal="true" excludeEmpty="true"/></additional>',
            encoding="utf-8",
        )
        cmd = sumo_command(
            build_dir,
            plan,
            begin,
            [
                "--end",
                str(end),
                "--statistic-output",
                str(work / "stats.xml"),
                "--no-warnings",
                "true",
                "--duration-log.disable",
                "true",
            ],
        )
        i = cmd.index("-a")
        cmd[i + 1] += f",{add}"
        t0 = time.monotonic()
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode:
            raise RuntimeError(res.stderr[-600:])
        net = sumolib.net.readNet(str(build_dir / "network.net.xml"))
        via = via_lane_map(net)
        turns: dict[str, float] = {}
        for iv in ET.parse(work / "turns.xml").getroot().iter("interval"):
            h = int(float(iv.get("begin")) // 3600)
            for lane in iv.iter("lane"):
                if (pair := via.get(lane.get("id"))) is not None:
                    key = f"{pair[0]}|{pair[1]}|{h}"
                    turns[key] = turns.get(key, 0.0) + float(lane.get("entered") or 0)
        root = ET.parse(work / "stats.xml").getroot()
        veh = {k: int(float(v)) for k, v in root.find("vehicles").attrib.items()}
        tele = int(float(root.find("teleports").get("total", 0)))
    return {
        "start_h": start_h,
        "hours": hours,
        "turns": turns,
        "vehicles": veh,
        "teleports": tele,
        "runtime_s": round(time.monotonic() - t0, 1),
    }


def score(build_dir: Path, runs: list[dict], date: str) -> dict:
    """GEH<5 share over the scored hours of all windows, per junction and for the corridor."""
    m = load_manifest(build_dir)
    day = load_day(date)
    sim: dict[tuple[str, str, int], float] = {}
    hours: set[int] = set()
    for r in runs:
        hours |= set(range(r["start_h"], r["start_h"] + r["hours"]))
        for k, v in r["turns"].items():
            a, b, h = k.split("|")
            sim[(a, b, int(h))] = v
    per: dict[str, list[float]] = {}
    for mv in day.veh:
        apps = m["approaches"].get(mv.junction_id, {})
        if mv.from_approach not in apps or mv.to_approach not in apps:
            continue
        frm, to = apps[mv.from_approach]["in_edge"], apps[mv.to_approach]["out_edge"]
        counts = day.hourly(mv)
        for h in hours:
            per.setdefault(mv.junction_id, []).append(geh(sim.get((frm, to, h), 0.0), counts[h]))
    allv = [g for v in per.values() for g in v]
    return {
        "corridor": sum(g < GEH_OK for g in allv) / max(1, len(allv)),
        "junctions": {j: round(sum(g < GEH_OK for g in v) / len(v), 3) for j, v in sorted(per.items())},
        "n": len(allv),
    }


def evaluate(build_dir: Path, windows=DEFAULT_WINDOWS, plan: str = "demand2", workers: int = 3) -> dict:
    """Run all windows in parallel and score against 11 May (calibration) and 12 May (validation)."""
    with ThreadPoolExecutor(workers) as pool:
        runs = list(pool.map(lambda w: run_window(build_dir, w[0], w[1], plan=plan), windows))
    loaded = sum(r["vehicles"].get("loaded", 0) for r in runs)
    waiting = sum(r["vehicles"].get("waiting", 0) for r in runs)
    return {
        "calibration": score(build_dir, runs, config.CALIBRATION_DATE),
        "validation": score(build_dir, runs, config.VALIDATION_DATE),
        "unserved_share": waiting / max(1, loaded),
        "loaded": loaded,
        "waiting": waiting,
        "teleports": sum(r["teleports"] for r in runs),
        "runtime_s": max(r["runtime_s"] for r in runs),
        "windows": [f"{(w[0] + 8) % 24:02d}:00+{w[1]}h" for w in windows],
    }


if __name__ == "__main__":
    import sys

    print(json.dumps(evaluate(Path(sys.argv[1])), indent=2, default=float))
