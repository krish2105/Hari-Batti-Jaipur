"""W1 diagnostics: evidence for why the simulated corridor gridlocks.

1. Saturation flow SUMO actually achieves with our vehicle types (one signalised test road,
   oversaturated demand), for the survey mix with the sublane model vs cars only.
2. Mid-block access share of the fitted demand.
3. Lane assumptions vs the counted flow per lane.
4. Variants V0-V4: the same fast evaluator (sim.evaluate) on the step-by-step fixes, so the report
   can show which change moved the score.
Run: uv run python -m sim.diagnose            (saturation flow only, seconds)
     uv run python -m sim.diagnose --variants (also V0-V4; about 1-2 h, writes reports/calibration_diagnostics.json)
"""

import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from . import config
from .build import write_vtypes
from .config import CALIBRATION_DATE, load_assumptions
from .demand import load_day, vehicle_mix
from .sumo_env import binary, run_binary

GREEN, AMBER, RED = 60, 3, 57  # 120 s cycle, 50% green


def _test_road(work: Path, lanes: int) -> Path:
    (work / "t.nod.xml").write_text(
        '<nodes><node id="a" x="-600" y="0"/><node id="s" x="0" y="0" type="traffic_light"/>'
        '<node id="b" x="300" y="0"/></nodes>'
    )
    (work / "t.edg.xml").write_text(
        f'<edges><edge id="in" from="a" to="s" numLanes="{lanes}" speed="13.89"/>'
        f'<edge id="out" from="s" to="b" numLanes="{lanes}" speed="13.89"/></edges>'
    )
    net = work / "t.net.xml"
    run_binary(
        "netconvert",
        [
            "-n",
            str(work / "t.nod.xml"),
            "-e",
            str(work / "t.edg.xml"),
            "-o",
            str(net),
            "--lefthand",
            "true",
            "--tls.default-type",
            "static",
        ],
    )
    g, y, r = "G" * lanes, "y" * lanes, "r" * lanes
    (work / "tls.add.xml").write_text(
        f'<additional><tlLogic id="s" type="static" programID="t" offset="0">'
        f'<phase duration="{GREEN}" state="{g}"/><phase duration="{AMBER}" state="{y}"/>'
        f'<phase duration="{RED}" state="{r}"/></tlLogic>'
        f'<inductionLoop id="stopline" lane="out_0" pos="5" period="99999" file="e1_0.xml"/>'
        + "".join(
            f'<inductionLoop id="l{i}" lane="out_{i}" pos="5" period="99999" file="e1_{i}.xml"/>'
            for i in range(1, lanes)
        )
        + "</additional>"
    )
    return net


def saturation_flow(mix: dict[str, float] | None, sublane: bool, lanes: int = 3, cycles: int = 12) -> dict:
    """Vehicles per hour of green per lane discharged from a standing queue."""
    a = load_assumptions()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        net = _test_road(work, lanes)
        write_vtypes(work / "vtypes.add.xml", mix or {"car": 1.0}, a)
        end = cycles * (GREEN + AMBER + RED)
        (work / "r.rou.xml").write_text(
            f'<routes><route id="r" edges="in out"/><flow id="f" type="mix" route="r" begin="0" end="{end}" '
            f'vehsPerHour="{2600 * lanes}" departLane="best" departSpeed="max" departPosLat="random"/></routes>'
        )
        cmd = [
            binary("sumo"),
            "-n",
            str(net),
            "-r",
            str(work / "r.rou.xml"),
            "-a",
            f"{work / 'vtypes.add.xml'},{work / 'tls.add.xml'}",
            "--end",
            str(end),
            "--no-step-log",
            "true",
            "--no-warnings",
            "true",
            "--seed",
            "1",
        ]
        if sublane:
            cmd += ["--lateral-resolution", str(a["sublane"]["lateral_resolution_m"])]
        res = subprocess.run(cmd, cwd=work, capture_output=True, text=True, check=False)
        if res.returncode:
            raise RuntimeError(res.stderr[-800:])
        passed = sum(
            float(iv.get("nVehContrib", 0))
            for f in work.glob("e1_*.xml")
            for iv in ET.parse(f).getroot().iter("interval")
        )
    green_h = cycles * GREEN / 3600
    per_lane = passed / green_h / lanes
    return {"vehicles": int(passed), "veh_per_green_h_per_lane": round(per_lane)}


def _lanes(main: int, cross: int) -> dict:
    return {"main_road": main, "cross_road": cross}


# id, what changed, build overrides, build folder suffix, reuse routes from (same edges)
VARIANTS = [
    ("V0", "Starting point: midblock access stubs on, 3 / 2 lanes",
     {"network": {"midblock_access": True, "turn_lanes": "auto"}, "lanes": _lanes(3, 2)}, "v0-mid", None),
    ("V1", "Midblock stubs off (no survey basis)",
     {"network": {"midblock_access": False, "turn_lanes": "auto"}, "lanes": _lanes(3, 2)}, "v1-nomid", None),
    ("V2", "V1 + dedicated right-turn lane",
     {"network": {"midblock_access": False, "turn_lanes": "dedicated_right"}, "lanes": _lanes(3, 2)},
     "v2-nomid-rt", "v1-nomid"),
    ("V3", "V1 + one more lane per direction (4 / 3)",
     {"network": {"midblock_access": False, "turn_lanes": "auto"}, "lanes": _lanes(4, 3)}, "v3-nomid-lanes", "v1-nomid"),
    ("V4", "V3 + dedicated right-turn lane",
     {"network": {"midblock_access": False, "turn_lanes": "dedicated_right"}, "lanes": _lanes(4, 3)},
     "v4-nomid-rt-lanes", "v1-nomid"),
]  # fmt: skip


def variants() -> list[dict]:
    """Build (or reuse) and score each variant on the same windows as the Optuna search."""
    from .build import build
    from .evaluate import evaluate

    out = []
    for vid, label, over, name, routes in VARIANTS:
        src = config.BUILD_DIR / f"schematic-{routes}" if routes else None
        b = build("schematic", name=name, overrides=over, routes_from=src)
        r = evaluate(b)
        row = {
            "id": vid,
            "label": label,
            "calibration_geh_share": round(r["calibration"]["corridor"], 4),
            "validation_geh_share": round(r["validation"]["corridor"], 4),
            "unserved_share": round(r["unserved_share"], 4),
            "teleports": r["teleports"],
            "windows": r["windows"],
        }
        print(f"[diagnose] {vid}: {json.dumps(row)}", flush=True)
        out.append(row)
    return out


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", action="store_true", help="also score V0-V4 (slow)")
    args = ap.parse_args()
    day = load_day(CALIBRATION_DATE)
    mix = vehicle_mix(day)
    pcu_per_veh = sum(sum(s) for s in day.pcu.values()) / sum(sum(s) for s in day.veh.values())
    rows = {
        "survey mix, sublane on": saturation_flow(mix, True),
        "survey mix, sublane off": saturation_flow(mix, False),
        "cars only, sublane off": saturation_flow(None, False),
    }
    for r in rows.values():
        r["pcu_per_green_h_per_lane"] = round(r["veh_per_green_h_per_lane"] * pcu_per_veh)
    result = {"pcu_per_vehicle_survey": round(pcu_per_veh, 3), "saturation": rows}
    if args.variants:
        result["variants"] = variants()
        path = config.REPORTS_DIR / "calibration_diagnostics.json"
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"[diagnose] wrote {path.relative_to(config.ROOT)}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
