"""W1 diagnostics: evidence for why the simulated corridor gridlocks.

1. Saturation flow SUMO actually achieves with our vehicle types (one signalised test road,
   oversaturated demand), for the survey mix with the sublane model vs cars only.
2. Mid-block access share of the fitted demand.
3. Lane assumptions vs the counted flow per lane.
Run: uv run python -m sim.diagnose
"""

import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

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


def main() -> None:
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
    print(json.dumps({"pcu_per_vehicle_survey": round(pcu_per_veh, 3), "saturation": rows}, indent=2))


if __name__ == "__main__":
    main()
