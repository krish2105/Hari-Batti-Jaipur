"""Corridor geometry for the study: junction chainages and projecting GPS points onto the corridor.

Junction positions come from apps/mobile/src/data/corridor.json (built from the registry; positions
are ASSUMED until verified), ordered J08 (west) -> J03 (east).
"""

import json
import math
from functools import lru_cache
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CORRIDOR_JSON = ROOT / "apps/mobile/src/data/corridor.json"


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


@lru_cache
def corridor() -> dict:
    """{"junctions": [...], "chainage": [...], "limit": km/h} ordered west -> east."""
    d = json.loads(CORRIDOR_JSON.read_text(encoding="utf-8"))
    js = d["junctions"]
    ch = [0.0]
    for a, b in pairwise(js):
        ch.append(ch[-1] + haversine_m((a["lat"], a["lng"]), (b["lat"], b["lng"])))
    return {"junctions": js, "chainage": ch, "limit": d["speedLimitKmh"], "positionStatus": "ASSUMED"}


def _xy(lat: float, lng: float, lat0: float) -> tuple[float, float]:
    return (lng * 111_320 * math.cos(math.radians(lat0)), lat * 110_574)


def project(lat: float, lng: float) -> tuple[float, float]:
    """(chainage along the corridor in m, distance off the corridor in m)."""
    c = corridor()
    js, ch = c["junctions"], c["chainage"]
    lat0 = js[0]["lat"]
    p = _xy(lat, lng, lat0)
    best = (0.0, float("inf"))
    for i in range(len(js) - 1):
        a, b = _xy(js[i]["lat"], js[i]["lng"], lat0), _xy(js[i + 1]["lat"], js[i + 1]["lng"], lat0)
        dx, dy = b[0] - a[0], b[1] - a[1]
        seg2 = dx * dx + dy * dy or 1.0
        u = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / seg2))
        off = math.hypot(p[0] - (a[0] + u * dx), p[1] - (a[1] + u * dy))
        if off < best[1]:
            best = (ch[i] + u * (ch[i + 1] - ch[i]), off)
    return best


def at_chainage(s: float) -> tuple[float, float]:
    """Lat/lng of a chainage (extrapolated linearly beyond both ends)."""
    c = corridor()
    js, ch = c["junctions"], c["chainage"]
    i = (
        0
        if s <= ch[1]
        else len(ch) - 2
        if s >= ch[-2]
        else next(k for k in range(len(ch) - 1) if ch[k] <= s <= ch[k + 1])
    )
    u = (s - ch[i]) / (ch[i + 1] - ch[i])
    a, b = js[i], js[i + 1]
    return (a["lat"] + u * (b["lat"] - a["lat"]), a["lng"] + u * (b["lng"] - a["lng"]))
