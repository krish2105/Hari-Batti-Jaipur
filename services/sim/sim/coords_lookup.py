"""Look up CANDIDATE coordinates for J01-J08 on OpenStreetMap (free, public APIs).

Writes data/junction_coords_candidates.csv for a human to check on Google Maps.
It NEVER writes to data/junction_registry.csv — copy verified values there yourself.

How candidates are found:
  1. Overpass: named roads in a Mansarovar bounding box. For each junction we collect the road
     names the survey itself uses (junction name, both sets of approach labels, and "Madhyam Marg",
     which the DAY1 files use for the corridor road) and find where two such roads cross.
  2. Nominatim: a text search for the junction name.
Only public junction/road names are sent; no survey counts. Map data © OpenStreetMap
contributors (ODbL). Nominatim is called at most once per second with an identifying User-Agent.
"""

import csv
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from . import config

BBOX = (26.80, 75.72, 26.90, 75.81)  # south, west, north, east (Mansarovar / Sanganer area)
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "HariBatti-pilot/0.1 (local junction coordinate lookup)"
CORRIDOR_ROAD = "Madhyam Marg"  # DAY1 survey labels for J04-J08 name the main-road arm this way
CLUSTER_M = 60  # crossing nodes closer than this are one junction


def _get(url: str, params: dict | None = None, data: dict | None = None, timeout: int = 120) -> dict:
    """GET (or POST form data) and parse JSON."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as res:  # fixed https URLs above
        return json.load(res)


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def names_match(a: str, b: str) -> bool:
    """Loose match of two road names: 'B2BYPASS' ~ 'B2 Bypass Road', 'Vijay path' ~ 'Vijaya Path',
    'Patel Marg Crossing' ~ 'Patel Marg'. Different spellings of different places do not match
    ('Mansarover Metro' vs 'Mansarovar Link Road')."""
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    wa, wb = a.lower().split(), b.lower().split()
    first_ok = (wa[0].startswith(wb[0]) or wb[0].startswith(wa[0])) and min(len(wa[0]), len(wb[0])) >= 4
    second_ok = len(wa) > 1 and len(wb) > 1 and norm(wa[1])[:3] == norm(wb[1])[:3]
    return first_ok and second_ok


def dist_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot((a[0] - b[0]) * 111_000, (a[1] - b[1]) * 111_000 * math.cos(math.radians(a[0])))


def search_terms(row: dict) -> tuple[str, list[str]]:
    """(junction-name road, all road names the survey uses for this junction)."""
    core = re.sub(r"\s*junction\s*$", "", row["junction_name"], flags=re.IGNORECASE).strip()
    terms = [core]
    for col in ("approaches_used", "approaches_in_day1_file"):
        terms += [t.strip() for t in (row.get(col) or "").split("|") if t.strip()]
    if row["junction_id"] not in ("J01", "J02"):
        terms.append(CORRIDOR_ROAD)
    return core, list(dict.fromkeys(terms))


def fetch_osm() -> tuple[list[dict], dict[int, tuple[float, float]], list[tuple[float, float]]]:
    """Named roads (with node coordinates) and traffic-signal nodes inside BBOX."""
    s, w, n, e = BBOX
    q = (
        f'[out:json][timeout:90];(way["highway"]["name"]({s},{w},{n},{e}););(._;>;);out body;'
        f'node["highway"="traffic_signals"]({s},{w},{n},{e});out body;'
    )
    d = _get(OVERPASS_URL, data={"data": q}, timeout=150)
    nodes = {el["id"]: (el["lat"], el["lon"]) for el in d["elements"] if el["type"] == "node"}
    signals = [
        (el["lat"], el["lon"])
        for el in d["elements"]
        if el["type"] == "node" and el.get("tags", {}).get("highway") == "traffic_signals"
    ]
    ways = [el for el in d["elements"] if el["type"] == "way"]
    return ways, nodes, signals


def crossings(ways: list[dict], nodes: dict) -> list[dict]:
    """Every place where two differently named roads share nodes, clustered to one point."""
    names_at: dict[int, set[str]] = defaultdict(set)
    for w in ways:
        for nid in w["nodes"]:
            names_at[nid].add(w["tags"]["name"])
    raw: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
    for nid, names in names_at.items():
        for a, b in combinations(sorted(names), 2):
            if norm(a) != norm(b):
                raw[(a, b)].append(nodes[nid])
    out = []
    for (a, b), pts in raw.items():
        clusters: list[list[tuple[float, float]]] = []
        for p in pts:
            for c in clusters:
                if dist_m(p, c[0]) < CLUSTER_M:
                    c.append(p)
                    break
            else:
                clusters.append([p])
        for c in clusters:
            out.append(
                {"roads": (a, b), "lat": sum(p[0] for p in c) / len(c), "lng": sum(p[1] for p in c) / len(c)}
            )
    return out


def nominatim(query: str) -> list[dict]:
    s, w, n, e = BBOX
    params = {"q": query, "format": "jsonv2", "limit": 3, "viewbox": f"{w},{n},{e},{s}", "bounded": 1}
    if email := os.environ.get("NOMINATIM_EMAIL"):
        params["email"] = email  # optional, only if you set it yourself
    time.sleep(1.1)  # Nominatim usage policy: max 1 request per second
    return _get(NOMINATIM_URL, params=params, timeout=30)


def lookup(out_path: Path = config.CANDIDATES_CSV) -> Path:
    """Find candidates for every registry junction and write the CSV. Returns its path."""
    with config.REGISTRY_CSV.open(newline="", encoding="utf-8") as f:
        registry = list(csv.DictReader(f))
    print("[coords] Overpass: fetching named roads and signals around Mansarovar ...", flush=True)
    ways, nodes, signals = fetch_osm()
    xs = crossings(ways, nodes)
    rows: list[dict] = []
    for r in registry:
        jid = r["junction_id"]
        core, terms = search_terms(r)
        cands = []
        for x in xs:
            a, b = x["roads"]
            ta = [t for t in terms if names_match(t, a)]
            tb = [t for t in terms if names_match(t, b)]
            if ta and tb and len(set(ta) | set(tb)) >= 2:  # two different survey road names cross here
                has_core = names_match(core, a) or names_match(core, b)
                cands.append(
                    {
                        **x,
                        "confidence": "medium" if has_core else "low",
                        "method": "OSM crossing of survey road names",
                        "evidence": f"{a} × {b} (survey names: {', '.join(sorted(set(ta) | set(tb)))})",
                    }
                )
        for hit in nominatim(f"{core}, Mansarovar, Jaipur"):
            cands.append(
                {
                    "roads": (),
                    "lat": float(hit["lat"]),
                    "lng": float(hit["lon"]),
                    "confidence": "low",
                    "method": "Nominatim text search",
                    "evidence": hit["display_name"][:120],
                }
            )
        cands.sort(key=lambda c: (c["confidence"] != "medium", c["method"]))
        if not cands:
            rows.append(
                {
                    "junction_id": jid,
                    "junction_name": r["junction_name"],
                    "rank": "",
                    "candidate_lat": "",
                    "candidate_lng": "",
                    "confidence": "not found",
                    "method": "",
                    "evidence": f"no OSM crossing or search hit for: {', '.join(terms)}",
                    "nearest_osm_signal_m": "",
                    "also_matches": "",
                    "google_maps_url": "",
                    "verify": "TRUE",
                }
            )
        for i, c in enumerate(cands[:3], 1):
            near = min((dist_m((c["lat"], c["lng"]), s) for s in signals), default=None)
            rows.append(
                {
                    "junction_id": jid,
                    "junction_name": r["junction_name"],
                    "rank": i,
                    "candidate_lat": f"{c['lat']:.6f}",
                    "candidate_lng": f"{c['lng']:.6f}",
                    "confidence": c["confidence"],
                    "method": c["method"],
                    "evidence": c["evidence"],
                    "nearest_osm_signal_m": f"{near:.0f}" if near is not None else "",
                    "also_matches": "",
                    "google_maps_url": f"https://www.google.com/maps?q={c['lat']:.6f},{c['lng']:.6f}",
                    "verify": "TRUE",
                }
            )
    # flag the same point proposed for two junctions
    for a in rows:
        if not a["candidate_lat"]:
            continue
        pa = (float(a["candidate_lat"]), float(a["candidate_lng"]))
        others = sorted(
            {
                b["junction_id"]
                for b in rows
                if b["candidate_lat"]
                and b["junction_id"] != a["junction_id"]
                and dist_m(pa, (float(b["candidate_lat"]), float(b["candidate_lng"]))) < CLUSTER_M
            }
        )
        a["also_matches"] = " ".join(others)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        wtr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wtr.writeheader()
        wtr.writerows(rows)
    print(
        f"[coords] wrote {out_path.relative_to(config.ROOT)} — CANDIDATES ONLY, check each on Google Maps "
        "and copy verified lat/lng into data/junction_registry.csv yourself",
        flush=True,
    )
    return out_path
