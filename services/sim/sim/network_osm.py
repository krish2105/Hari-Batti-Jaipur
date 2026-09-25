"""OSM network: real Mansarovar roads from OpenStreetMap (used once coordinates exist).

Default when all 8 junctions in data/junction_registry.csv have lat/lng (`make sim-calibrate`
then re-runs everything on it). `--coords data/junction_coords_candidates.csv` builds the same
thing from UNVERIFIED candidates, for testing only; junctions without a candidate are left out.

Steps:
  1. Overpass download of drivable roads around the junctions (+500 m) -> data/osm/*.osm (ODbL)
  2. netconvert (left-hand traffic, joined junction clusters, street names kept)
  3. each pilot junction = nearest real intersection within 80 m; a signal is set there
  4. arms: the "Mansarover Metro" arm is the one pointing at the next junction towards J08
     (J08: away from J07); the rest follow clockwise using the survey's L/S/R layout.
     Street names are only a cross-check and any disagreement is flagged.
"""

import csv
import math
import urllib.parse
import urllib.request
from pathlib import Path

from . import config
from .config import Assumptions
from .layout import SIDES, JunctionLayout
from .network_schematic import NetworkInfo
from .registry import Junction
from .sumo_env import run_binary, sumolib

ROAD_TYPES = "motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|service"
MATCH_RADIUS_M = 80
ORDER = ["J03", "J04", "J05", "J06", "J07", "J08"]  # Sanganer Stadium end -> Mansarovar Metro end
SPUR = ["J01", "J02"]


def load_coords(
    junctions: list[Junction], coords_csv: Path | None
) -> tuple[dict[str, tuple[float, float]], list[str]]:
    """Registry coordinates, or rank-1 candidates from the candidates CSV (test mode)."""
    if coords_csv is None:
        return {j.id: (j.lat, j.lng) for j in junctions if j.has_coords}, []
    coords, flags = {}, ["CANDIDATE coords — unverified (test only): " + str(coords_csv.name)]
    with coords_csv.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["rank"] == "1" and r["candidate_lat"] and r["junction_id"] not in coords:
                coords[r["junction_id"]] = (float(r["candidate_lat"]), float(r["candidate_lng"]))
    missing = [j.id for j in junctions if j.id not in coords]
    if missing:
        flags.append(f"No candidate coordinates for {missing}: left out of this test network")
    return coords, flags


def download_osm(coords: dict[str, tuple[float, float]], out_file: Path) -> None:
    """Overpass: drivable roads in the junctions' bounding box + ~500 m."""
    lats = [c[0] for c in coords.values()]
    lngs = [c[1] for c in coords.values()]
    pad_lat, pad_lng = 0.0045, 0.0050
    s, n = min(lats) - pad_lat, max(lats) + pad_lat
    w, e = min(lngs) - pad_lng, max(lngs) + pad_lng
    q = (
        f'[out:xml][timeout:120];(way["highway"~"^({ROAD_TYPES})(_link)?$"]({s},{w},{n},{e}););'
        "(._;>;);out meta;"
    )
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=urllib.parse.urlencode({"data": q}).encode(),
        headers={"User-Agent": "HariBatti-pilot/0.1 (network build)"},
    )
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=180) as res:  # fixed https URL above
        out_file.write_bytes(res.read())


def bearing(frm: tuple[float, float], to: tuple[float, float]) -> float:
    """Compass bearing in degrees (0 = north, clockwise) between two SUMO x/y points."""
    return math.degrees(math.atan2(to[0] - frm[0], to[1] - frm[1])) % 360


def _arms(node) -> list[dict]:
    """Physical arms at a node: incoming edge, matching outgoing edge, outward bearing, street name."""
    c = node.getCoord()
    arms = []
    for e_in in node.getIncoming():
        if e_in.getFunction() == "internal":
            continue
        shape = e_in.getShape()
        b = bearing(c, shape[-2] if len(shape) > 1 else e_in.getFromNode().getCoord())
        best, gap = None, 999.0
        for e_out in node.getOutgoing():
            s2 = e_out.getShape()
            d = abs(
                (bearing(c, s2[1] if len(s2) > 1 else e_out.getToNode().getCoord()) - b + 180) % 360 - 180
            )
            if d < gap:
                best, gap = e_out, d
        arms.append({"in": e_in, "out": best if gap < 30 else None, "bearing": b, "name": e_in.getName()})
    return sorted(arms, key=lambda a: a["bearing"])


def check_arm_names(jid: str, junctions: list[Junction], apps: dict[str, dict]) -> list[str]:
    """Cross-check with OSM street names: both main arms should be on one road, both cross arms on
    another, and the road the junction is named after (e.g. 'Rajat Path') should be a cross arm."""
    by_side = {v["side"]: (v.get("osm_name") or "") for v in apps.values()}
    out = []
    main = {by_side[s] for s in ("W", "E") if by_side.get(s)}
    cross = {by_side[s] for s in ("N", "S") if by_side.get(s)}
    if len(main) > 1:
        out.append(f"{jid}: main-road arms are on different OSM roads {sorted(main)} — check the arm order")
    core = next(j.name for j in junctions if j.id == jid).replace("Junction", "").strip().lower()
    if main and any(core[:5] in m.lower() for m in main):
        out.append(
            f"{jid}: the road it is named after ({core!r}) is on the main-road arms — arms look rotated"
        )
    if main & cross:
        out.append(f"{jid}: main and cross arms share OSM road {sorted(main & cross)} — check the location")
    return out


def build_osm(
    out_dir: Path,
    junctions: list[Junction],
    layouts: dict[str, JunctionLayout],
    lanes: dict[str, dict[str, int]],
    a: Assumptions,
    coords_csv: Path | None = None,
    geometry: str = "OSM",
) -> NetworkInfo:
    """Download, convert and map the real roads. Lanes come from OSM, not from assumptions."""
    coords, flags = load_coords(junctions, coords_csv)
    osm = config.OSM_FILE if coords_csv is None else config.OSM_FILE.with_name("mansarovar_candidate.osm")
    if not osm.exists():
        print(f"[build] downloading OSM extract -> {osm.relative_to(config.ROOT)}", flush=True)
        download_osm(coords, osm)
    raw = out_dir / "osm_raw.net.xml"
    common = ["--lefthand", "true", "--no-turnarounds", "true", "--tls.default-type", "static"]
    run_binary(
        "netconvert",
        [
            "--osm-files",
            str(osm),
            "-o",
            str(raw),
            *common,
            "--geometry.remove",
            "true",
            "--roundabouts.guess",
            "true",
            "--ramps.guess",
            "true",
            "--junctions.join",
            "true",
            "--tls.guess-signals",
            "true",
            "--tls.join",
            "true",
            "--remove-edges.isolated",
            "true",
            "--keep-edges.by-vclass",
            "passenger",
            "--output.street-names",
            "true",
        ],
        log=out_dir / "netconvert_osm.log",
    )
    net = sumolib.net.readNet(str(raw))

    # 1) nearest real intersection for each junction
    node_of: dict[str, object] = {}
    for jid, (lat, lng) in coords.items():
        x, y = net.convertLonLat2XY(lng, lat)
        best = min(
            (
                n
                for n in net.getNodes()
                if len([e for e in n.getIncoming() if e.getFunction() != "internal"]) >= 3
            ),
            key=lambda n: math.dist((x, y), n.getCoord()),
            default=None,
        )
        if best is None or math.dist((x, y), best.getCoord()) > MATCH_RADIUS_M:
            flags.append(f"{jid}: no intersection within {MATCH_RADIUS_M} m of its coordinates — left out")
            continue
        node_of[jid] = best

    # 2) arms -> survey approaches (on the raw network; edge ids stay the same in step 3)
    approaches: dict[str, dict[str, dict]] = {}
    tls: dict[str, str] = {}
    for jid, node in node_of.items():
        arms = _arms(node)
        lay = layouts[jid]
        if len(arms) != 4:
            flags.append(f"{jid}: intersection has {len(arms)} arms, survey has 4 — check the location")
        chain = ORDER if jid in ORDER else SPUR
        i = chain.index(jid)
        toward = chain[i + 1] if i + 1 < len(chain) else chain[i - 1]
        if toward in node_of:
            tb = bearing(node.getCoord(), node_of[toward].getCoord())
            if i + 1 >= len(chain):
                tb = (tb + 180) % 360  # last junction: the Metro arm points away from its neighbour
        else:
            tb = arms[0]["bearing"]
            flags.append(f"{jid}: neighbour {toward} not mapped; Metro-side arm guessed")
        start = min(range(len(arms)), key=lambda k: abs((arms[k]["bearing"] - tb + 180) % 360 - 180))
        approaches[jid] = {}
        for k, side in enumerate(SIDES):  # W (Metro side), then clockwise N, E, S
            if k >= len(arms):
                break
            arm = arms[(start + k) % len(arms)]
            name = lay.approach_at[side]
            if arm["out"] is None:
                flags.append(f"{jid} {name}: no outgoing edge on this arm (one-way?) — UNMATCHED")
                continue
            approaches[jid][name] = {
                "side": side,
                "in_edge": arm["in"].getID(),
                "out_edge": arm["out"].getID(),
                "lanes": lanes[jid][name],
                "osm_lanes": arm["in"].getLaneNumber(),
                "osm_name": arm["name"],
            }
        flags += check_arm_names(jid, junctions, approaches[jid])
        tls[jid] = node.getID()

    # 3) signals at every mapped node (OSM often lacks signal tags here) + lanes on approach edges
    #    from the registry, else assumptions.toml (OSM rarely tags lanes; netconvert would guess 1)
    patch = out_dir / "lanes_patch.edg.xml"
    rows = [
        f'  <edge id="{v[key]}" numLanes="{v["lanes"]}"/>'
        for apps in approaches.values()
        for v in apps.values()
        for key in ("in_edge", "out_edge")
    ]
    patch.write_text("<edges>\n" + "\n".join(dict.fromkeys(rows)) + "\n</edges>\n", encoding="utf-8")
    final = out_dir / "network.net.xml"
    run_binary(
        "netconvert",
        [
            "-s",
            str(raw),
            "-e",
            str(patch),
            "-o",
            str(final),
            *common,
            "--tls.set",
            ",".join(n.getID() for n in node_of.values()),
        ],
        log=out_dir / "netconvert_tls.log",
    )
    flags.append(f"{config.GEOMETRY_LABELS[geometry]}; map data © OpenStreetMap contributors (ODbL)")
    flags.append("Approach lanes: registry lanes_per_approach, else assumptions.toml (OSM lane tags ignored)")
    return NetworkInfo(final, geometry, approaches, {}, flags, tls)
