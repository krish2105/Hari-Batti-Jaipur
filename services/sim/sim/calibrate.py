"""Calibration + validation report: GEH per movement per hour, plus gridlock indicators.

One headless, as-fast-as-possible run of the 11 May demand (default the whole 24-h survey day).
Simulated hourly turning counts (M) are compared with the survey (C):
    GEH = sqrt(2 (M - C)^2 / (M + C))            target: GEH < 5 for >= 85% of movement-hours
  pass 1  calibration: against 11 May (the day the demand was built from)
  pass 2  validation:  against 12 May (independent day, J03-J08 only)
Also reported, so gridlock is visible rather than hidden: teleports, vehicles never inserted
(unserved demand, per origin approach) and the maximum queue per approach per hour.
The report holds hourly aggregates only — never raw survey sheets.
"""

import json
import math
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import traci

from . import config
from .build import load_manifest
from .demand import load_day
from .registry import slug
from .stream import sumo_command
from .timings import PLAN_LABELS

GEH_OK = 5.0
TARGET_SHARE = 0.85
WARMUP_HOURS = 1  # the network starts empty at 08:00, so hour 1 is shown but not scored


def geh(m: float, c: float) -> float:
    """GEH statistic for one simulated (m) vs counted (c) hourly flow. 0 when both are 0."""
    if m + c == 0:
        return 0.0
    return math.sqrt(2 * (m - c) ** 2 / (m + c))


def share_ok(values: list[float], limit: float = GEH_OK) -> float:
    """Share of GEH values under the limit (0-1)."""
    return sum(v < limit for v in values) / len(values) if values else float("nan")


def verdict(share: float, target: float = TARGET_SHARE) -> str:
    if math.isnan(share):
        return "no data"
    return "PASS" if share >= target else "FAIL"


# ---------------------------------------------------------------- run


def _write_detectors(run_dir: Path, manifest: dict, net_lanes: dict[str, list[tuple[str, float]]]) -> Path:
    """E2 queue detectors on every approach lane + hourly turn-count output."""
    lines = ["<additional>"]
    for jid, apps in manifest["approaches"].items():
        for name, info in apps.items():
            for lane_id, length in net_lanes[info["in_edge"]]:
                det = f"e2|{jid}|{slug(name)}|{lane_id}"
                lines.append(
                    f'  <laneAreaDetector id="{det}" lane="{lane_id}" pos="0" endPos="{length - 0.1:.1f}" '
                    f'friendlyPos="true" period="3600" file="e2.xml"/>'
                )
    # turn counts: vehicles entering each junction-internal lane (one per from->to connection)
    lines.append(
        '  <laneData id="turns" period="3600" file="turns_sim.xml" withInternal="true" excludeEmpty="true"/>'
    )
    lines.append("</additional>")
    path = run_dir / "detectors.add.xml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _route_origins(routes_file: Path) -> dict[str, str]:
    """vehicle id -> first edge of its route (to map vehicles never inserted to an approach)."""
    origins: dict[str, str] = {}
    vid = None
    pat_v, pat_r = re.compile(r'<vehicle id="([^"]+)"'), re.compile(r'<route edges="(\S+)')
    with routes_file.open(encoding="utf-8") as f:
        for line in f:
            if m := pat_v.search(line):
                vid = m.group(1)
            elif vid and (m := pat_r.search(line)):
                origins[vid] = m.group(1)
                vid = None
    return origins


def run_calibration(build_dir: Path, hours: int = 24, plan: str = "demand2") -> Path:
    """Run SUMO headless and write services/sim/reports/calibration.md. Returns the report path."""
    manifest = load_manifest(build_dir)
    run_dir = build_dir / "calibration"
    run_dir.mkdir(exist_ok=True)
    from .sumo_env import sumolib  # local import keeps module import cheap

    net = sumolib.net.readNet(str(build_dir / "network.net.xml"))
    net_lanes = {e.getID(): [(ln.getID(), ln.getLength()) for ln in e.getLanes()] for e in net.getEdges()}
    detectors = _write_detectors(run_dir, manifest, net_lanes)
    end = hours * 3600
    extra = [
        "--end",
        str(end),
        "-a",
        f"{build_dir / 'vtypes.add.xml'},{build_dir / f'tls_{plan}.add.xml'},{detectors}",
        "--statistic-output",
        str(run_dir / "stats.xml"),
        "--log",
        str(run_dir / "sumo.log"),  # includes the teleport warnings
        "--duration-log.statistics",
        "true",
    ]
    cmd = sumo_command(build_dir, plan, 0, extra)
    # sumo_command already has one -a; drop it so ours (with detectors) is the only one
    i = cmd.index("-a")
    del cmd[i : i + 2]
    origins = _route_origins(build_dir / "routes.rou.xml")
    edge_to_approach = {
        info["in_edge"]: f"{jid} {name}"
        for jid, apps in manifest["approaches"].items()
        for name, info in apps.items()
    }
    edge_to_approach |= {acc["in_edge"]: f"Midblock access {mid}" for mid, acc in manifest["access"].items()}

    print(
        f"[calibrate] {manifest['geometry_label']} | {PLAN_LABELS[plan]} | {hours} h headless run ...",
        flush=True,
    )
    t0 = time.monotonic()
    traci.start(cmd)
    for tls in manifest["tls_ids"].values():
        traci.trafficlight.setProgram(tls, "haribatti")
    pending_by_hour: dict[int, Counter] = {}
    step = 0
    while step < end:
        step = min(step + config.SLOT_S, end)
        traci.simulationStep(float(step))
        if step % 3600 == 0 or step == end:
            pend = Counter(
                edge_to_approach.get(origins.get(v, ""), "?") for v in traci.simulation.getPendingVehicles()
            )
            pending_by_hour[(step - 1) // 3600] = pend
            print(
                f"[calibrate]   {sim_hour_label(step)} done, {sum(pend.values()):,} waiting to enter "
                f"({time.monotonic() - t0:.0f}s)",
                flush=True,
            )
    traci.close()
    runtime = time.monotonic() - t0
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "hours": hours,
                "plan": plan,
                "runtime_s": runtime,
                "pending_by_hour": {str(h): dict(c) for h, c in pending_by_hour.items()},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return report_from_run(build_dir)


def report_from_run(build_dir: Path) -> Path:
    """Rebuild calibration.md from the saved outputs of the last run (no new simulation)."""
    from .sumo_env import sumolib

    run_dir = build_dir / "calibration"
    saved = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    net = sumolib.net.readNet(str(build_dir / "network.net.xml"))
    pending = {int(h): Counter(c) for h, c in saved["pending_by_hour"].items()}
    return write_report(
        build_dir,
        run_dir,
        load_manifest(build_dir),
        saved["hours"],
        saved["plan"],
        pending,
        saved["runtime_s"],
        via_lane_map(net),
    )


def sim_hour_label(sim_s: int) -> str:
    return f"{(sim_s // 3600 + config.SURVEY_DAY_START_HOUR) % 24:02d}:00"


def hour_label(h: int) -> str:
    """Survey hour index (0 = 08:00-09:00) -> '08-09'."""
    a = (h + config.SURVEY_DAY_START_HOUR) % 24
    return f"{a:02d}-{(a + 1) % 24:02d}"


# ---------------------------------------------------------------- parse outputs


def via_lane_map(net) -> dict[str, tuple[str, str]]:
    """First internal ('via') lane of every connection -> (from edge, to edge)."""
    out: dict[str, tuple[str, str]] = {}
    for edge in net.getEdges():
        for conns in edge.getOutgoing().values():
            for c in conns:
                if c.getViaLaneID():
                    out[c.getViaLaneID()] = (c.getFrom().getID(), c.getTo().getID())
    return out


def parse_sim_turns(path: Path, via: dict[str, tuple[str, str]]) -> dict[tuple[str, str, int], float]:
    """(from_edge, to_edge, hour) -> simulated vehicles, from laneData on junction-internal lanes."""
    out: dict[tuple[str, str, int], float] = defaultdict(float)
    for interval in ET.parse(path).getroot().iter("interval"):
        h = int(float(interval.get("begin")) // 3600)
        for lane in interval.iter("lane"):
            if (pair := via.get(lane.get("id"))) is not None:
                out[(*pair, h)] += float(lane.get("entered") or 0)
    return out


def parse_queues(path: Path) -> dict[tuple[str, str, int], dict]:
    """(junction, approach slug, hour) -> max queue (m, longest lane) and queued vehicles (sum of lanes)."""
    out: dict[tuple[str, str, int], dict] = {}
    for iv in ET.parse(path).getroot().iter("interval"):
        _, jid, ap, _lane = iv.get("id").split("|")
        h = int(float(iv.get("begin")) // 3600)
        rec = out.setdefault((jid, ap, h), {"m": 0.0, "veh": 0.0})
        rec["m"] = max(rec["m"], float(iv.get("maxJamLengthInMeters", 0)))
        rec["veh"] += float(iv.get("maxJamLengthInVehicles", 0))
    return out


def parse_stats(path: Path) -> dict:
    root = ET.parse(path).getroot()
    v = root.find("vehicles").attrib
    t = root.find("teleports").attrib
    return {
        "vehicles": {k: int(float(x)) for k, x in v.items()},
        "teleports": {k: int(float(x)) for k, x in t.items()},
    }


def parse_teleports(path: Path, manifest: dict) -> Counter:
    """Teleports per junction approach, from SUMO's warning messages (lane id -> approach)."""
    lane_to = {
        info["in_edge"]: f"{jid} {name}"
        for jid, apps in manifest["approaches"].items()
        for name, info in apps.items()
    }
    pat = re.compile(r"Teleporting vehicle '[^']+'; ([^,]+), lane='([^']+)'")
    out: Counter = Counter()
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if m := pat.search(line):
                edge = m.group(2).rsplit("_", 1)[0]
                out[
                    (lane_to.get(edge, edge if not edge.startswith(":") else "inside a junction"), m.group(1))
                ] += 1
    return out


# ---------------------------------------------------------------- report


def compare(manifest: dict, sim: dict, date: str, hours: int) -> list[dict]:
    """One row per junction movement-hour with survey count, simulated count and GEH."""
    day = load_day(date)
    rows = []
    for m, _series in sorted(
        day.veh.items(), key=lambda kv: (kv[0].junction_id, kv[0].from_approach, kv[0].to_approach)
    ):
        apps = manifest["approaches"].get(m.junction_id, {})
        if m.from_approach not in apps or m.to_approach not in apps:
            continue
        frm, to = apps[m.from_approach]["in_edge"], apps[m.to_approach]["out_edge"]
        for h, c in enumerate(day.hourly(m)[:hours]):
            s = sim.get((frm, to, h), 0.0)
            rows.append(
                {
                    "junction": m.junction_id,
                    "movement": f"{m.from_approach} → {m.to_approach} ({m.turn})",
                    "hour": h,
                    "survey": c,
                    "sim": s,
                    "geh": geh(s, c),
                }
            )
    return rows


def lane_load(manifest: dict, date: str) -> list[dict]:
    """Busiest-hour counted vehicles per assumed lane for every approach, highest first."""
    day = load_day(date)
    per: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0] * 24)
    for m in day.veh:
        for h, v in enumerate(day.hourly(m)):
            per[(m.junction_id, m.from_approach)][h] += v
    rows = []
    for (jid, name), series in per.items():
        info = manifest["approaches"].get(jid, {}).get(name)
        if not info:
            continue
        h = max(range(24), key=series.__getitem__)
        rows.append(
            {
                "approach": f"{jid} {name}",
                "lanes": info["lanes"],
                "hour": h,
                "veh": series[h],
                "per_lane": series[h] / info["lanes"],
            }
        )
    return sorted(rows, key=lambda r: -r["per_lane"])


def _scored(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["hour"] >= WARMUP_HOURS]


def demand_fit(build_dir: Path, manifest: dict) -> dict:
    """Vehicles written by routeSampler, its static GEH, and the share of midblock-stub trips."""
    first_last: list[tuple[str, str]] = []
    with (build_dir / "routes.rou.xml").open(encoding="utf-8") as f:
        for line in f:
            if "<route edges=" in line:
                edges = line.split('edges="', 1)[1].split('"', 1)[0].split()
                first_last.append((edges[0], edges[-1]))
    n = len(first_last) or 1
    acc_in = {a["in_edge"] for a in manifest["access"].values()}
    acc_out = {a["out_edge"] for a in manifest["access"].values()}
    log = (build_dir / "routeSampler.log").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"avg interval GEH%: .*?mean ([0-9.]+)", log)
    return {
        "vehicles": len(first_last),
        "from_access": sum(a in acc_in for a, _ in first_last) / n,
        "to_access": sum(b in acc_out for _, b in first_last) / n,
        "static_geh": f"GEH<5 for {float(m.group(1)):.0f}% of counted movements per 15 min" if m else "n/a",
    }


def report_header(manifest: dict, plan: str, hours: int, runtime_s: float) -> list[str]:
    """Title block: says which network (schematic/OSM) and which timing plan the numbers come from."""
    timing = manifest["plans"][plan]
    field = any(p["timing"] == "FIELD" for p in timing.values())
    return [
        "# HariBatti simulator — calibration & validation report",
        "",
        f"> **{manifest['geometry_label']}**  ",
        f"> Timing: **{PLAN_LABELS[plan]}**" + ("" if field else " (ASSUMED — no field timings yet)") + "  ",
        (
            f"> Generated {datetime.now(UTC).astimezone(config.IST):%Y-%m-%d %H:%M} IST · simulated {hours} h "
            f"from 08:00 IST in {runtime_s / 60:.1f} min · SUMO sublane model on"
        ),
        "",
    ]


def write_report(
    build_dir: Path,
    run_dir: Path,
    manifest: dict,
    hours: int,
    plan: str,
    pending_by_hour: dict[int, Counter],
    runtime_s: float,
    via: dict[str, tuple[str, str]],
) -> Path:
    sim = parse_sim_turns(run_dir / "turns_sim.xml", via)
    queues = parse_queues(run_dir / "e2.xml")
    stats = parse_stats(run_dir / "stats.xml")
    teleports = parse_teleports(run_dir / "sumo.log", manifest)
    cal = compare(manifest, sim, config.CALIBRATION_DATE, hours)
    val = compare(manifest, sim, config.VALIDATION_DATE, hours)
    val_junctions = sorted({r["junction"] for r in val})
    junctions = list(manifest["approaches"])

    L: list[str] = report_header(manifest, plan, hours, runtime_s)
    w = L.append
    w(
        "Counts marked **Survey, May 2026** come from `data/processed/tmc_clean.csv` (hourly aggregates only). "
        "Counts marked **SIM** are simulated. GEH = √(2(M−C)²/(M+C)), M = SIM, C = Survey. "
        f"Target: GEH < {GEH_OK:g} for at least {TARGET_SHARE:.0%} of movement-hours. "
        f"Hour 08–09 is warm-up (the network starts empty) and is shown but not scored."
    )
    w("")

    # summary
    w("## Summary")
    w("")
    w("| Junction | Calibration (11 May) GEH<5 | Result | Validation (12 May) GEH<5 | Result |")
    w("| --- | --- | --- | --- | --- |")
    for j in junctions:
        c = share_ok([r["geh"] for r in _scored(cal) if r["junction"] == j])
        if j in val_junctions:
            v = share_ok([r["geh"] for r in _scored(val) if r["junction"] == j])
            vtxt, vres = f"{v:.0%}", verdict(v)
        else:
            vtxt, vres = "no 12 May data", "—"
        w(f"| {j} | {c:.0%} | {verdict(c)} | {vtxt} | {vres} |")
    cc = share_ok([r["geh"] for r in _scored(cal)])
    vv = share_ok([r["geh"] for r in _scored(val)])
    w(f"| **Corridor** | **{cc:.0%}** | **{verdict(cc)}** | **{vv:.0%}** (J03–J08) | **{verdict(vv)}** |")
    w("")

    # gridlock
    veh, tp = stats["vehicles"], stats["teleports"]
    never = sum(pending_by_hour.get(max(pending_by_hour), Counter()).values()) if pending_by_hour else 0
    w("## Gridlock check")
    w("")
    w("| Indicator | Value |")
    w("| --- | --- |")
    w(f"| Vehicles loaded (SIM demand in window) | {veh.get('loaded', 0):,} |")
    w(f"| Vehicles inserted | {veh.get('inserted', 0):,} |")
    w(f"| **Vehicles never inserted by end of run (unserved demand)** | **{never:,}** |")
    w(f"| Vehicles still driving at end | {veh.get('running', 0):,} |")
    w(
        f"| **Teleports** (jam / yield / wrong lane) | **{tp.get('total', 0):,}** "
        f"({tp.get('jam', 0):,} / {tp.get('yield', 0):,} / {tp.get('wrongLane', 0):,}) |"
    )
    w("")
    w("### Unserved demand by origin approach (vehicles waiting to enter at the end of each hour)")
    w("")
    origins = sorted(
        {o for c in pending_by_hour.values() for o in c},
        key=lambda o: -max(c.get(o, 0) for c in pending_by_hour.values()),
    )
    if origins:
        hrs = sorted(pending_by_hour)
        w("| Origin | " + " | ".join(hour_label(h) for h in hrs) + " |")
        w("| --- |" + " --- |" * len(hrs))
        for o in origins[:20]:
            w(f"| {o} | " + " | ".join(f"{pending_by_hour[h].get(o, 0):,}" for h in hrs) + " |")
    else:
        w("None — every vehicle entered the network.")
    w("")
    w("### Teleports by approach")
    w("")
    if teleports:
        w("| Where | Reason | Count |")
        w("| --- | --- | --- |")
        for (where, why), n in teleports.most_common(20):
            w(f"| {where} | {why} | {n:,} |")
    else:
        w("None.")
    w("")
    w("### Max queue per approach (SIM, worst hour)")
    w("")
    w("| Approach | Max queue (m, longest lane) | Max queued vehicles (all lanes) | Worst hour |")
    w("| --- | --- | --- | --- |")
    worst: dict[tuple[str, str], tuple[float, float, int]] = {}
    for (jid, ap, h), q in queues.items():
        if (jid, ap) not in worst or q["m"] > worst[(jid, ap)][0]:
            worst[(jid, ap)] = (q["m"], q["veh"], h)
    for (jid, ap), (m, veh_q, h) in sorted(worst.items(), key=lambda kv: -kv[1][0]):
        w(f"| {jid} {ap} | {m:,.0f} | {veh_q:,.0f} | {hour_label(h)} |")
    w("")

    # demand fit (static) + how much the assumed midblock stubs carry
    w("## Demand fit before simulation (routeSampler)")
    w("")
    fit = demand_fit(build_dir, manifest)
    w(
        f"- Survey turning vehicles to match (11 May): **{manifest['survey_turn_counts']:,}**; "
        f"routes written: **{fit['vehicles']:,}** vehicles"
    )
    w(
        f"- Static route fit: {fit['static_geh']} (every count matched before any driving happens — the GEH above "
        "measures what the simulated network can actually deliver)"
    )
    if manifest["access"]:
        w(
            f"- Trips starting at a midblock access stub (assumed): **{fit['from_access']:.0%}**; ending at one: "
            f"**{fit['to_access']:.0%}**. These absorb the differences between neighbouring junctions' counts "
            "(side lanes, parking, driveways — or approach labels that are mixed up)."
        )
    if manifest["geometry"] == "SCHEMATIC":
        w(
            "- Corridor order: OpenStreetMap puts J03 at the Sanganer Stadium end and J08 near Mansarovar Metro; "
            "the counts alone fit either order about equally, so this needs the real coordinates to confirm."
        )
    w("")

    # capacity table
    w("## Webster flow ratio Y per junction (PM peak, Survey, May 2026)")
    w("")
    w("Y > 1 means no fixed cycle can serve the counted demand with the assumed lanes and saturation flow.")
    w("")
    w("| Junction | 2-phase, free left | Approach-wise (4-stage) |")
    w("| --- | --- | --- |")
    for j, y in manifest["webster_y"].items():
        two = f"{y['two_phase_y']:.2f}" + (
            " — demand exceeds 2-phase capacity" if y["two_phase_y"] > 1 else ""
        )
        four = f"{y['approach_wise_y']:.2f}" + (
            " — demand exceeds 4-stage capacity" if y["approach_wise_y"] > 1 else ""
        )
        w(f"| {j} | {two} | {four} |")
    w("")

    # flow per assumed lane
    w("## Why capacity binds: counted flow per assumed lane (busiest hour, Survey, May 2026)")
    w("")
    w(
        "Vehicles per hour per assumed lane on each approach, before any red time. A single SUMO lane with a "
        "green light all hour carries roughly 1,800–2,000 vehicles/h, and a signal gives each approach only part "
        "of the hour — so values near or above that show where the assumed lanes, not the demand, are the limit. "
        "Real Mansarovar traffic is lane-less and half two-wheelers, so the real road carries more per metre of width."
    )
    w("")
    w("| Approach | Assumed lanes | Busiest hour | Vehicles/h (Survey) | Vehicles/h per lane |")
    w("| --- | --- | --- | --- | --- |")
    for row in lane_load(manifest, config.CALIBRATION_DATE)[:16]:
        w(
            f"| {row['approach']} | {row['lanes']} | {hour_label(row['hour'])} | {row['veh']:,.0f} | {row['per_lane']:,.0f} |"
        )
    w("")

    # per-junction hourly
    w("## Hourly GEH<5 share per junction (calibration, 11 May)")
    w("")
    w("| Hour | " + " | ".join(junctions) + " |")
    w("| --- |" + " --- |" * len(junctions))
    for h in range(hours):
        cells = []
        for j in junctions:
            vals = [r["geh"] for r in cal if r["junction"] == j and r["hour"] == h]
            cells.append(f"{share_ok(vals):.0%}" if vals else "—")
        w(f"| {hour_label(h)}{' (warm-up)' if h < WARMUP_HOURS else ''} | " + " | ".join(cells) + " |")
    w("")

    # worst
    w("## 15 worst movement-hours (calibration, 11 May)")
    w("")
    w("| Junction | Movement | Hour | Survey, May 2026 | SIM | GEH |")
    w("| --- | --- | --- | --- | --- | --- |")
    for r in sorted(_scored(cal), key=lambda r: -r["geh"])[:15]:
        w(
            f"| {r['junction']} | {r['movement']} | {hour_label(r['hour'])} | {r['survey']:,.0f} | {r['sim']:,.0f} | {r['geh']:.1f} |"
        )
    w("")

    # plans + assumptions
    w("## Timing plan used (ASSUMED)")
    w("")
    w("| Junction | Cycle (s) | Greens (s) | Webster Y | Note |")
    w("| --- | --- | --- | --- | --- |")
    for j, p in manifest["plans"][plan].items():
        greens = ", ".join(str(ph["duration_s"]) for ph in p["phases"] if ph["kind"] == "green")
        note = "; ".join(p["notes"]) or ""
        y = f"{p['webster_y']:.2f}" if p.get("webster_y") is not None else "—"
        w(f"| {j} | {p['cycle_s']} | {greens} | {y} | {note} |")
    w("")
    w("## Assumptions and flags")
    w("")
    for f in manifest["flags"]:
        w(f"- {f}")
    a = manifest["assumptions"]
    w(
        f"- Saturation flow {a['capacity']['saturation_flow_pcu_per_lane_h']} PCU/h/lane, lost time "
        f"{a['capacity']['lost_time_per_phase_s']} s/phase, amber {a['timing']['amber_s']} s, all-red {a['timing']['all_red_s']} s"
    )
    w(
        f"- Sublane model: lateral resolution {a['sublane']['lateral_resolution_m']} m; two-wheelers "
        f"latAlignment={a['sublane']['two_wheeler_lat_alignment']}, minGapLat={a['sublane']['two_wheeler_min_gap_lat_m']} m"
    )
    w("- Signal offsets are all 0 (no coordination yet); vehicle mix is the corridor-wide survey share")
    w(
        f"- Demand: routeSampler fitted {manifest['survey_turn_counts']:,} surveyed turning vehicles (11 May) "
        f"with {manifest['candidate_routes']} candidate routes"
    )
    w("")
    w("## Data caveat")
    w("")
    network = (
        "This is a schematic stand-in, not the real road layout: link lengths, "
        if manifest["geometry"] == "SCHEMATIC"
        else "This uses OpenStreetMap roads, but "
    )
    w(
        network + "lane counts, signal timings and "
        "coordination are assumptions until coordinates, lanes and stopwatch timings are collected. A FAIL here "
        "says the assumed network cannot reproduce the counts — most likely causes are capacity (lanes, saturation "
        "flow, phasing) and the midblock-access simplification — not that the survey is wrong. Nothing was tuned "
        "to force a pass."
    )
    w("")
    w("Input hashes: " + ", ".join(f"`{k}` {v}" for k, v in manifest["inputs"].items()))
    w("")

    config.REPORTS_DIR.mkdir(exist_ok=True)
    report = config.REPORTS_DIR / "calibration.md"
    report.write_text("\n".join(L), encoding="utf-8")
    (run_dir / "summary.json").write_text(
        json.dumps(
            {"calibration_share": cc, "validation_share": vv, "never_inserted": never, "teleports": tp},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"[calibrate] corridor GEH<5: calibration {cc:.0%} ({verdict(cc)}), validation {vv:.0%} ({verdict(vv)})"
    )
    print(f"[calibrate] report: {report.relative_to(config.ROOT)}")
    return report
