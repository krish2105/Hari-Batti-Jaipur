"""Plan Studio: compare a baseline and a proposed signal plan in the same simulated window.

Both runs use the same demand, seed and window, so the difference comes from the plan only.
A proposal is either another plan id (demand2 / webster4 / even) for all junctions, or a custom
2-phase plan (cycle + main/cross green) for ONE junction with the baseline everywhere else.
Output: JSON with mean delay (time loss), stops, CO2 and completed trips per variant. SIM numbers.
This is a what-if tool: it never sends anything to a real signal.
"""

import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .build import load_manifest, state_string
from .clock import clock_to_sim_offset, parse_hhmm
from .config import load_assumptions
from .stream import sumo_command
from .timings import PLAN_LABELS


def custom_tls(
    build_dir: Path,
    base_plan: str,
    junction_id: str,
    cycle_s: int,
    main_green_s: int,
    cross_green_s: int,
    out: Path,
) -> str:
    """Copy the baseline programs, replacing one junction with a custom 2-phase free-left plan."""
    a = load_assumptions()
    t = a["timing"]
    inter = int(t["amber_s"]) + int(t["all_red_s"])
    if main_green_s + cross_green_s + 2 * inter != cycle_s:
        raise ValueError(
            f"greens {main_green_s}+{cross_green_s} + 2x{inter}s intergreen must equal cycle {cycle_s}"
        )
    if min(main_green_s, cross_green_s) < int(t["min_green_s"]):
        raise ValueError(f"each green must be at least {t['min_green_s']} s")
    m = load_manifest(build_dir)
    links = {int(k): tuple(v) for k, v in m["links"][junction_id].items()}
    n = 1 + max(links)
    free_left = {(s, "L"): "G" for s in "WNES"}
    phases = []
    for grp, g in ((("W", "E"), main_green_s), (("N", "S"), cross_green_s)):
        green = {(s, "S"): "G" for s in grp} | {(s, "R"): "g" for s in grp} | free_left
        amber = {(s, t2): "y" for s in grp for t2 in ("S", "R")} | free_left
        phases += [(g, green), (int(t["amber_s"]), amber), (int(t["all_red_s"]), dict(free_left))]
    tree = ET.parse(build_dir / f"tls_{base_plan}.add.xml")
    root = tree.getroot()
    tls_id = m["tls_ids"][junction_id]
    for logic in root.findall("tlLogic"):
        if logic.get("id") == tls_id:
            for ph in list(logic):
                logic.remove(ph)
            for dur, moves in phases:
                ET.SubElement(logic, "phase", duration=str(dur), state=state_string(moves, links, n))
    tree.write(out, encoding="unicode")
    return f"Custom 2-phase at {junction_id}: cycle {cycle_s} s, greens {main_green_s}/{cross_green_s} s"


def _run(build_dir: Path, tls_file: Path, begin: int, end: int, measure_from: int, work: Path) -> dict:
    """One headless SUMO run; averages over trips that start inside the measured window."""
    trip = work / f"{tls_file.stem}.tripinfo.xml"
    stats = work / f"{tls_file.stem}.stats.xml"
    cmd = sumo_command(
        build_dir,
        "demand2",
        begin,
        [
            "--end",
            str(end),
            "--tripinfo-output",
            str(trip),
            "--statistic-output",
            str(stats),
            "--device.emissions.probability",
            "1",
            "--no-warnings",
            "true",
            "--duration-log.disable",
            "true",
        ],
    )
    i = cmd.index("-a")
    cmd[i + 1] = f"{build_dir / 'vtypes.add.xml'},{tls_file}"
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    n = delay = stops = co2 = 0.0
    for t in ET.parse(trip).getroot().iter("tripinfo"):
        if float(t.get("depart")) < measure_from:
            continue
        n += 1
        delay += float(t.get("timeLoss"))
        stops += float(t.get("waitingCount"))
        em = t.find("emissions")
        if em is not None:
            co2 += float(em.get("CO2_abs")) / 1e6  # mg -> kg
    tele = ET.parse(stats).getroot().find("teleports").attrib
    return {
        "tripsCompleted": int(n),
        "meanDelayS": round(delay / n, 1) if n else None,
        "meanStops": round(stops / n, 2) if n else None,
        "co2Kg": round(co2, 1),
        "co2PerTripG": round(1000 * co2 / n) if n else None,
        "teleports": int(tele.get("total", 0)),
    }


def simulate(
    build_dir: Path,
    baseline: str = "even",
    proposed: str | None = "demand2",
    junction_id: str | None = None,
    custom: dict | None = None,
    start: str = "18:15",
    minutes: int = 15,
    warmup_min: int = 5,
) -> dict:
    """Run baseline and proposal side by side and return a before/after comparison."""
    begin = max(0, clock_to_sim_offset(parse_hhmm(start)) - warmup_min * 60)
    measure_from = begin + warmup_min * 60
    end = measure_from + minutes * 60
    with tempfile.TemporaryDirectory(prefix="plan-studio-") as tmp:
        work = Path(tmp)
        base_tls = work / "baseline.add.xml"
        base_tls.write_text(
            (build_dir / f"tls_{baseline}.add.xml").read_text(encoding="utf-8"), encoding="utf-8"
        )
        prop_tls = work / "proposed.add.xml"
        if custom:
            if not junction_id:
                raise ValueError("a custom plan needs a junction")
            label = custom_tls(
                build_dir,
                baseline,
                junction_id,
                int(custom["cycle_s"]),
                int(custom["main_green_s"]),
                int(custom["cross_green_s"]),
                prop_tls,
            )
        else:
            prop_tls.write_text(
                (build_dir / f"tls_{proposed}.add.xml").read_text(encoding="utf-8"), encoding="utf-8"
            )
            label = PLAN_LABELS[proposed]
        with ThreadPoolExecutor(2) as pool:
            fb = pool.submit(_run, build_dir, base_tls, begin, end, measure_from, work)
            fp = pool.submit(_run, build_dir, prop_tls, begin, end, measure_from, work)
            before, after = fb.result(), fp.result()

    def change(k: str) -> float | None:
        if before[k] in (None, 0) or after[k] is None:
            return None
        return round(100 * (after[k] - before[k]) / before[k], 1)

    m = load_manifest(build_dir)
    return {
        "source": "SIM",
        "geometryLabel": m["geometry_label"],
        "window": f"{start} + {minutes} min (after {warmup_min} min warm-up)",
        "baseline": {"label": PLAN_LABELS[baseline], **before},
        "proposed": {"label": label, **after},
        # per-trip values, because a better plan also lets more trips finish in the same window
        "changePct": {k: change(k) for k in ("meanDelayS", "meanStops", "co2PerTripG", "tripsCompleted")},
        "note": "Simulated what-if on the calibration demand (Survey, May 2026). Never applied to a real signal.",
    }


def main_json(args) -> None:
    custom = json.loads(args.custom) if args.custom else None
    print(
        json.dumps(
            simulate(
                args.build_dir,
                args.baseline,
                args.proposed,
                args.junction,
                custom,
                args.start,
                args.minutes,
                args.warmup,
            ),
            ensure_ascii=False,
        )
    )
