"""Schematic network – coordinates pending.

A straight-line stand-in for the real roads, used until data/junction_registry.csv has lat/lng.
Arm positions come from the survey's own turn labels (see layout.py). Everything else is assumed
and listed in `flags`:
  - J03-J08 in a row, `link_spacing_m` apart, Metro side west, Stadium side east. The order follows
    OpenStreetMap: Madhyam Marg crosses Vijaya Path, Patel Marg, VT Road and Rajat Path (J04-J07)
    running from the Sanganer Stadium end (south-east) to Mansarovar Metro (north-west), so going
    west -> east here the row is J08, J07, ..., J03
  - J01 -> J02 as a separate pair on the B2 Bypass side (west of J03, drawn above it);
    no road joins them to J03 because the survey names no approach that proves the link
  - one "midblock access" stub on every shared link, to absorb the differences between the
    counts at neighbouring junctions (side lanes, parking, driveways)
Edge IDs: every junction side has `{J}_{side}_in` (towards the junction) and `{J}_{side}_out`.
"""

from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from xml.sax.saxutils import quoteattr

from .config import Assumptions
from .layout import JunctionLayout
from .sumo_env import run_binary

# listed west (Mansarovar Metro / B2 Bypass side) -> east (Sanganer Stadium / Sumer Nagar side)
CORRIDORS = [["J08", "J07", "J06", "J05", "J04", "J03"], ["J01", "J02"]]
CORRIDOR_ORIGIN = {"J08": (0.0, 0.0), "J01": (-1900.0, 900.0)}  # schematic positions (m)
OFFSET = {"W": (-1, 0), "E": (1, 0), "N": (0, 1), "S": (0, -1)}


@dataclass
class NetworkInfo:
    """What the rest of the build needs to know about a network, whatever its source."""

    net_file: Path
    geometry: str  # "SCHEMATIC" or "OSM"/"OSM_CANDIDATE"
    # junction -> approach name -> {"side", "in_edge", "out_edge", "lanes"}
    approaches: dict[str, dict[str, dict]]
    # midblock stubs: id -> {"between": [A, B], "in_edge", "out_edge"}
    access: dict[str, dict] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)
    # junction -> SUMO traffic-light id (schematic: same as the junction id)
    tls: dict[str, str] = field(default_factory=dict)

    def tls_id(self, junction_id: str) -> str:
        return self.tls.get(junction_id, junction_id)


def _edge(eid: str, frm: str, to: str, lanes: int, speed_kmh: float, prio: int, name: str) -> str:
    return (
        f'  <edge id="{eid}" from="{frm}" to="{to}" numLanes="{lanes}" '
        f'speed="{speed_kmh / 3.6:.2f}" priority="{prio}" name={quoteattr(name)}/>'
    )


def build_schematic(
    out_dir: Path, layouts: dict[str, JunctionLayout], lanes: dict[str, dict[str, int]], a: Assumptions
) -> NetworkInfo:
    """Write nodes/edges, run netconvert (left-hand traffic) and describe the result."""
    g = a["geometry"]
    spacing, arm, acc_len = g["link_spacing_m"], g["arm_length_m"], g["midblock_access_m"]
    nodes: list[str] = []
    edges: list[str] = []
    approaches: dict[str, dict[str, dict]] = {}
    access: dict[str, dict] = {}

    def speed(side: str) -> float:
        return g["speed_main_kmh"] if side in ("W", "E") else g["speed_cross_kmh"]

    def prio(side: str) -> int:
        return 3 if side in ("W", "E") else 2

    for corridor in CORRIDORS:
        x0, y0 = CORRIDOR_ORIGIN[corridor[0]]
        pos = {j: (x0 + i * spacing, y0) for i, j in enumerate(corridor)}
        for j in corridor:
            x, y = pos[j]
            nodes.append(f'  <node id="{j}" x="{x:.1f}" y="{y:.1f}" type="traffic_light" tl="{j}"/>')
            approaches[j] = {}
        for i, j in enumerate(corridor):
            lay = layouts[j]
            for name, side in lay.side_of.items():
                n_lanes = lanes[j][name]
                approaches[j][name] = {
                    "side": side,
                    "in_edge": f"{j}_{side}_in",
                    "out_edge": f"{j}_{side}_out",
                    "lanes": n_lanes,
                }
                shared_east = side == "E" and i + 1 < len(corridor)
                shared_west = side == "W" and i > 0
                if shared_east or shared_west:
                    continue  # built once per link below
                x, y = pos[j]
                dx, dy = OFFSET[side]
                end = f"{j}_{side}_end"
                nodes.append(
                    f'  <node id="{end}" x="{x + dx * arm:.1f}" y="{y + dy * arm:.1f}" type="priority"/>'
                )
                edges.append(_edge(f"{j}_{side}_in", end, j, n_lanes, speed(side), prio(side), name))
                edges.append(_edge(f"{j}_{side}_out", j, end, n_lanes, speed(side), prio(side), name))
        # shared links with a midblock access stub in the middle
        for left, right in pairwise(corridor):
            mid = f"M_{left}_{right}"
            (xl, yl), (xr, _) = pos[left], pos[right]
            xm = (xl + xr) / 2
            nodes.append(f'  <node id="{mid}" x="{xm:.1f}" y="{yl:.1f}" type="priority"/>')
            acc = f"{mid}_acc"
            nodes.append(f'  <node id="{acc}" x="{xm:.1f}" y="{yl + acc_len:.1f}" type="priority"/>')
            ln = lanes[left][layouts[left].approach_at["E"]]
            rn = lanes[right][layouts[right].approach_at["W"]]
            main_name = f"{left}–{right} link"
            sp = g["speed_main_kmh"]
            edges += [
                _edge(f"{left}_E_out", left, mid, ln, sp, 3, main_name),
                _edge(f"{left}_E_in", mid, left, ln, sp, 3, main_name),
                _edge(f"{right}_W_in", mid, right, rn, sp, 3, main_name),
                _edge(f"{right}_W_out", right, mid, rn, sp, 3, main_name),
            ]
            acc_lanes = int(a["lanes"]["midblock_access"])
            edges += [
                _edge(f"{mid}_acc_in", acc, mid, acc_lanes, 30, 1, "Midblock access (assumed)"),
                _edge(f"{mid}_acc_out", mid, acc, acc_lanes, 30, 1, "Midblock access (assumed)"),
            ]
            access[mid] = {"between": [left, right], "in_edge": f"{mid}_acc_in", "out_edge": f"{mid}_acc_out"}

    nod, edg, net = out_dir / "schematic.nod.xml", out_dir / "schematic.edg.xml", out_dir / "network.net.xml"
    nod.write_text("<nodes>\n" + "\n".join(nodes) + "\n</nodes>\n", encoding="utf-8")
    edg.write_text("<edges>\n" + "\n".join(edges) + "\n</edges>\n", encoding="utf-8")
    run_binary(
        "netconvert",
        [
            "--node-files",
            str(nod),
            "--edge-files",
            str(edg),
            "--output-file",
            str(net),
            "--lefthand",
            "true",  # India drives on the left
            "--no-turnarounds",
            "true",
            "--tls.default-type",
            "static",
            "--junctions.corner-detail",
            "5",
            "--offset.disable-normalization",
            "true",
        ],
        log=out_dir / "netconvert.log",
    )
    flags = [
        "Schematic network – coordinates pending (no lat/lng in data/junction_registry.csv)",
        f"J03–J08 drawn in a straight row, {spacing} m apart (assumed spacing)",
        (
            "Row order J08 (Mansarovar Metro end) … J03 (Sanganer Stadium end), taken from OpenStreetMap "
            "(Madhyam Marg crossings; Metro station in the New Aatish Market area) — verify with real coordinates"
        ),
        "J01–J02 drawn as a separate pair on the B2 Bypass side; link to J03 unknown, so none is drawn",
        "Arm positions (N/S of each cross road) derived from the survey's L/S/R labels, left-hand traffic",
        "One midblock access stub per shared link absorbs count differences between neighbouring junctions",
        f"Outer arms {arm} m long; access stubs {acc_len} m (assumed)",
    ]
    return NetworkInfo(net, "SCHEMATIC", approaches, access, flags)
