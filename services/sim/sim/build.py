"""Build everything SUMO needs, into services/sim/build/<schematic|osm>/ (gitignored).

Steps:
  1. network (schematic now; OSM automatically once all 8 registry coordinates exist)
  2. signal programs for every plan (demand2, webster4, even; FIELD rows win)
  3. vehicle types (sublane model, two-wheelers filter between cars)
  4. survey turn counts per 15 min (calibration day) -> routeSampler -> 24-h routes
A manifest.json records input file hashes, so an unchanged build is reused.
"""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from . import config
from .config import Assumptions, load_assumptions
from .demand import DayCounts, load_day, vehicle_mix
from .layout import TURN_TARGET, JunctionLayout, derive_layout
from .network_schematic import NetworkInfo, build_schematic
from .registry import Junction, all_coords_present, load_registry, parse_lanes
from .sumo_env import run_tool, sumolib
from .timings import Plan, choose_plan, load_field_rows, load_pm_peak, webster_y_table

PLAN_IDS = ("demand2", "webster4", "even")
BUILD_VERSION = "p2-4"  # bump when the build logic changes, to force a rebuild

INPUTS = [
    config.REGISTRY_CSV,
    config.TMC_CSV,
    config.PM_PEAK_CSV,
    config.TIMINGS_CSV,
    config.ASSUMPTIONS_TOML,
]


def _rel(path: Path) -> str:
    """Path relative to the repo for log lines (absolute when outside it, e.g. in tests)."""
    return str(path.relative_to(config.ROOT)) if path.is_relative_to(config.ROOT) else str(path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def input_hashes(extra: list[Path] | None = None) -> dict[str, str]:
    files = INPUTS + (extra or [])
    return {str(p.relative_to(config.ROOT)): _sha(p) for p in files if p.exists()}


def choose_geometry(requested: str, junctions: list[Junction], coords_csv: Path | None) -> str:
    """auto -> OSM when every registry junction has lat/lng, else SCHEMATIC."""
    if coords_csv:
        return "OSM_CANDIDATE"
    if requested == "auto":
        return "OSM" if all_coords_present(junctions) else "SCHEMATIC"
    return requested.upper()


def resolve_lanes(
    junctions: list[Junction], layouts: dict[str, JunctionLayout], a: Assumptions
) -> tuple[dict[str, dict[str, int]], list[str]]:
    """Lanes per approach: registry value when filled, else assumptions.toml (flagged)."""
    lanes: dict[str, dict[str, int]] = {}
    flags: list[str] = []
    for j in junctions:
        given = parse_lanes(j.lanes_raw, j.approaches)
        lay = layouts[j.id]
        lanes[j.id] = {}
        for name in lay.side_of:
            if name in given:
                lanes[j.id][name] = given[name]
            else:
                key = "main_road" if lay.is_main(name) else "cross_road"
                lanes[j.id][name] = int(a["lanes"][key])
        if len(given) < len(lay.side_of):
            flags.append(j.id)
    if not flags:
        return lanes, []
    main, cross = a["lanes"]["main_road"], a["lanes"]["cross_road"]
    which = "all 8 junctions" if len(flags) == len(junctions) else ", ".join(flags)
    return lanes, [
        f"Lanes assumed at {which} (registry lanes_per_approach blank): main {main}, cross {cross}"
    ]


# ---------------------------------------------------------------- signal programs


def link_turns(net, info: NetworkInfo) -> dict[str, dict[int, tuple[str, str]]]:
    """For every signal: SUMO link index -> (approach side, turn L/S/R)."""
    out: dict[str, dict[int, tuple[str, str]]] = {}
    for jid, apps in info.approaches.items():
        side_in = {v["in_edge"]: v["side"] for v in apps.values()}
        side_out = {v["out_edge"]: v["side"] for v in apps.values()}
        links: dict[int, tuple[str, str]] = {}
        for in_lane, out_lane, idx in net.getTLS(info.tls_id(jid)).getConnections():
            s_in = side_in.get(in_lane.getEdge().getID())
            s_out = side_out.get(out_lane.getEdge().getID())
            if s_in is None or s_out is None:
                continue
            turn = next((t for t, target in TURN_TARGET[s_in].items() if target == s_out), None)
            if turn:
                links[idx] = (s_in, turn)
        out[jid] = links
    return out


def state_string(moves: dict[tuple[str, str], str], links: dict[int, tuple[str, str]], n: int) -> str:
    """SUMO state like 'GGrrgg...': one character per link index, red when not listed."""
    return "".join(moves.get(links.get(i, ("?", "?")), "r") for i in range(n))


def write_tls(path: Path, plans: dict[str, Plan], links, info: NetworkInfo, net) -> None:
    """One additional file per plan with a static tlLogic for every junction."""
    parts = ["<additional>"]
    for jid, plan in plans.items():
        tls_id = info.tls_id(jid)
        n = 1 + max(c[2] for c in net.getTLS(tls_id).getConnections())
        parts.append(f'  <tlLogic id="{tls_id}" type="static" programID="haribatti" offset="0">')
        for ph in plan.phases:
            parts.append(
                f'    <phase duration="{ph.duration_s}" state="{state_string(ph.moves, links[jid], n)}" '
                f'name="{ph.kind}"/>'
            )
        parts.append("  </tlLogic>")
    parts.append("</additional>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- vehicles and demand


def write_vtypes(path: Path, mix: dict[str, float], a: Assumptions) -> None:
    """Vehicle types for mixed Jaipur traffic, in a distribution weighted by the survey mix."""
    s = a["sublane"]
    car_lat = s["car_lat_alignment"]
    types = {
        "car": f'vClass="passenger" length="4.3" width="1.7" latAlignment="{car_lat}" minGapLat="0.6"',
        "two_wheeler": (
            f'vClass="motorcycle" length="1.9" width="0.8" minGap="1.0" '
            f'latAlignment="{s["two_wheeler_lat_alignment"]}" '
            f'minGapLat="{s["two_wheeler_min_gap_lat_m"]}" maxSpeedLat="1.5" lcSublane="2.0"'
        ),
        "lcv": f'vClass="delivery" length="5.5" width="2.0" latAlignment="{car_lat}" minGapLat="0.6"',
        "bus_truck": f'vClass="bus" length="10.0" width="2.5" latAlignment="{car_lat}" minGapLat="0.6"',
        "trailer": f'vClass="trailer" length="16.0" width="2.5" latAlignment="{car_lat}" minGapLat="0.6"',
        "slow": (
            'vClass="bicycle" length="2.0" width="0.9" maxSpeed="5.0" latAlignment="arbitrary" minGapLat="0.3"'
        ),
    }
    lines = ["<additional>", '  <vTypeDistribution id="mix">']
    for vid, share in mix.items():
        lines.append(f'    <vType id="{vid}" probability="{share:.5f}" {types[vid]}/>')
    lines += ["  </vTypeDistribution>", "</additional>"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_turn_counts(path: Path, day: DayCounts, info: NetworkInfo) -> int:
    """Survey vehicle counts per movement and 15-min slot as SUMO edgeRelations. Returns total."""
    by_slot: list[list[str]] = [[] for _ in range(96)]
    total = 0.0
    for m, series in day.veh.items():
        apps = info.approaches.get(m.junction_id, {})
        if m.from_approach not in apps or m.to_approach not in apps:
            continue  # unmatched approach (OSM only) - reported in the manifest
        frm, to = apps[m.from_approach]["in_edge"], apps[m.to_approach]["out_edge"]
        for slot, count in enumerate(series):
            if count > 0:
                by_slot[slot].append(f'    <edgeRelation from="{frm}" to="{to}" count="{count:g}"/>')
                total += count
    lines = ["<data>"]
    for slot, rels in enumerate(by_slot):
        b = slot * config.SLOT_S
        lines.append(f'  <interval id="slot{slot:02d}" begin="{b}" end="{b + config.SLOT_S}">')
        lines += rels
        lines.append("  </interval>")
    lines.append("</data>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return round(total)


def _fringe_routes(net, info: NetworkInfo) -> list[list[str]]:
    """OSM: trips between the network's dead-end edges that pass at least one pilot approach."""
    counted = {v["in_edge"] for apps in info.approaches.values() for v in apps.values()}

    def dead_end(node) -> bool:
        """A node that only connects to one neighbour (the edge of the downloaded area)."""
        neighbours = {e.getFromNode().getID() for e in node.getIncoming()} | {
            e.getToNode().getID() for e in node.getOutgoing()
        }
        return len(neighbours) <= 1

    sources = [e for e in net.getEdges() if e.getFunction() != "internal" and dead_end(e.getFromNode())]
    sinks = [e for e in net.getEdges() if e.getFunction() != "internal" and dead_end(e.getToNode())]
    routes = []
    for src in sources:
        for dst in sinks:
            if dst.getToNode() == src.getFromNode():
                continue
            path_edges, _ = net.getShortestPath(src, dst)
            if path_edges and counted & {e.getID() for e in path_edges}:
                routes.append([e.getID() for e in path_edges])
    return routes


def write_candidate_routes(path: Path, net, info: NetworkInfo) -> int:
    """Every possible trip from an outer arm (or access stub) to another, by shortest path."""
    if info.geometry != "SCHEMATIC":
        lines = ["<routes>"] + [
            f'  <route id="r{i}" edges="{" ".join(r)}"/>' for i, r in enumerate(_fringe_routes(net, info))
        ]
        path.write_text("\n".join([*lines, "</routes>"]) + "\n", encoding="utf-8")
        return len(lines) - 1
    sources, sinks = [], []
    for apps in info.approaches.values():
        for v in apps.values():
            e_in, e_out = net.getEdge(v["in_edge"]), net.getEdge(v["out_edge"])
            if e_in.getFromNode().getID() not in info.approaches:  # outer arm, not a shared link
                sources.append(e_in)
            if e_out.getToNode().getID() not in info.approaches:
                sinks.append(e_out)
    # a shared link's edges start/end at a midblock node, which is not a junction: exclude those
    mid_nodes = set(info.access)
    sources = [e for e in sources if e.getFromNode().getID() not in mid_nodes]
    sinks = [e for e in sinks if e.getToNode().getID() not in mid_nodes]
    for acc in info.access.values():
        sources.append(net.getEdge(acc["in_edge"]))
        sinks.append(net.getEdge(acc["out_edge"]))
    lines, n = ["<routes>"], 0
    for src in sources:
        for dst in sinks:
            if dst.getToNode().getID() == src.getFromNode().getID():
                continue  # no U-turn back to where you came from
            path_edges, _cost = net.getShortestPath(src, dst)
            if path_edges:
                ids = " ".join(e.getID() for e in path_edges)
                lines.append(f'  <route id="r{n}" edges="{ids}"/>')
                n += 1
    lines.append("</routes>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return n


# ---------------------------------------------------------------- main entry


def build(
    geometry: str = "auto",
    coords_csv: Path | None = None,
    force: bool = False,
    out_root: Path | None = None,
    demand: bool = True,
) -> Path:
    """Build (or reuse) the simulation inputs. Returns the build folder.

    out_root: where to build (default services/sim/build); demand=False skips routeSampler and
    writes an empty route file (used by fast tests).
    """
    a = load_assumptions()
    junctions = load_registry()
    geo = choose_geometry(geometry, junctions, coords_csv)
    out = (out_root or config.BUILD_DIR) / geo.lower()
    out.mkdir(parents=True, exist_ok=True)
    hashes = input_hashes([coords_csv] if coords_csv else None)
    manifest_path = out / "manifest.json"
    if manifest_path.exists() and not force:
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        same = old.get("inputs") == hashes and old.get("version") == BUILD_VERSION
        if same and (old.get("with_demand", True) or not demand):
            print(f"[build] up to date: {_rel(out)} ({config.GEOMETRY_LABELS[geo]})")
            return out

    print(f"[build] {config.GEOMETRY_LABELS[geo]}")
    day = load_day(config.CALIBRATION_DATE)
    layouts = {j.id: derive_layout(j.id, list(day.veh)) for j in junctions}
    lanes, lane_flags = resolve_lanes(junctions, layouts, a)

    if geo == "SCHEMATIC":
        info = build_schematic(out, layouts, lanes, a)
    else:
        from .network_osm import build_osm  # only needed once coordinates exist

        info = build_osm(out, junctions, layouts, lanes, a, coords_csv=coords_csv, geometry=geo)
        # real roads: use OSM lane counts wherever the registry gives none
        for j in junctions:
            given = parse_lanes(j.lanes_raw, j.approaches)
            for name, v in info.approaches.get(j.id, {}).items():
                if name not in given:
                    lanes[j.id][name] = v["lanes"]
        lane_flags = [f for f in lane_flags if not f.startswith("Lanes assumed")]

    net = sumolib.net.readNet(str(info.net_file), withPrograms=True)
    links = link_turns(net, info)
    pm_peak = load_pm_peak(config.CALIBRATION_DATE)
    field_rows = load_field_rows()
    plans_summary: dict[str, dict] = {}
    for pid in PLAN_IDS:
        plans = {
            j: choose_plan(pid, j, layouts[j].side_of, lanes[j], pm_peak[j], field_rows, a)
            for j in info.approaches
        }
        write_tls(out / f"tls_{pid}.add.xml", plans, links, info, net)
        plans_summary[pid] = {j: _plan_json(p) for j, p in plans.items()}

    write_vtypes(out / "vtypes.add.xml", vehicle_mix(day), a)
    survey_total = write_turn_counts(out / "turns_calibration.xml", day, info)
    if demand:
        n_routes = write_candidate_routes(out / "candidates.rou.xml", net, info)
        print(f"[build] routeSampler: {n_routes} candidate routes, {survey_total:,} surveyed turn counts")
        run_tool(
            "routeSampler.py",
            [
                "-r",
                str(out / "candidates.rou.xml"),
                "-t",
                str(out / "turns_calibration.xml"),
                "-o",
                str(out / "routes.rou.xml"),
                "--mismatch-output",
                str(out / "mismatch.xml"),
                "--optimize",
                "full",
                "--minimize-vehicles",
                "0.5",
                "--geh-ok",
                "5",
                "--attributes",
                'type="mix" departLane="best" departSpeed="max" departPosLat="random"',
                "--prefix",
                "v",
                "--seed",
                "42",
                "--threads",
                "4",
            ],
            log=out / "routeSampler.log",
        )
    else:
        n_routes = 0
        (out / "routes.rou.xml").write_text("<routes/>\n", encoding="utf-8")

    manifest = {
        "version": BUILD_VERSION,
        "geometry": geo,
        "geometry_label": config.GEOMETRY_LABELS[geo],
        "inputs": hashes,
        "calibration_date": config.CALIBRATION_DATE,
        "flags": info.flags + lane_flags,
        "assumptions": a.raw,
        "approaches": info.approaches,
        "access": info.access,
        "tls_ids": {j: info.tls_id(j) for j in info.approaches},
        "links": {j: {str(k): list(v) for k, v in lk.items()} for j, lk in links.items()},
        "plans": plans_summary,
        "webster_y": {
            j: webster_y_table(layouts[j].side_of, lanes[j], pm_peak[j], a) for j in info.approaches
        },
        "layout_inconsistencies": {j: list(lay.inconsistencies) for j, lay in layouts.items()},
        "candidate_routes": n_routes,
        "with_demand": demand,
        "survey_turn_counts": survey_total,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[build] done: {_rel(out)}")
    return out


def _plan_json(p: Plan) -> dict:
    d = asdict(p)
    d["cycle_s"] = p.cycle_s
    d["phases"] = [
        {
            "kind": ph.kind,
            "duration_s": ph.duration_s,
            "moves": {f"{s}{t}": c for (s, t), c in ph.moves.items()},
        }
        for ph in p.phases
    ]
    return d


def load_manifest(build_dir: Path) -> dict:
    return json.loads((build_dir / "manifest.json").read_text(encoding="utf-8"))
