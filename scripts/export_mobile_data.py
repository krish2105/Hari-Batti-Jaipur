"""Export the corridor for the mobile app's offline mode -> apps/mobile/src/data/corridor.json (committed).

Only public aggregates from apps/web/public/data/site.json: junction ids and names, CANDIDATE positions
(unverified OpenStreetMap matches), approach names (main road or cross road) and the ASSUMED signal plan.
No survey rows. Run from the repo root: python3 scripts/export_mobile_data.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "apps" / "web" / "public" / "data" / "site.json"
OUT = ROOT / "apps" / "mobile" / "src" / "data" / "corridor.json"
ORDER = ["J08", "J07", "J06", "J05", "J04", "J03"]  # west (Mansarovar Metro) -> east (Sanganer Stadium)


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main() -> None:
    site = json.loads(SITE.read_text(encoding="utf-8"))
    by_id = {j["id"]: j for j in site["junctions"]}
    out = []
    for jid in ORDER:
        j = by_id[jid]
        mains = [a["name"] for a in j["approaches"] if a["main"]]
        west = next((m for m in mains if "mansarover" in m.lower() or "metro" in m.lower()), mains[0])
        east = next(m for m in mains if m != west)
        out.append({
            "id": jid, "name": j["name"], "lat": j["position"]["lat"], "lng": j["position"]["lng"],
            "positionStatus": j["position"]["status"],
            # approach a driver uses when travelling east (coming from the west arm) or west
            "eastboundApproach": f"{jid}-{slug(west)}", "westboundApproach": f"{jid}-{slug(east)}",
            "approachNames": {f"{jid}-{slug(west)}": west, f"{jid}-{slug(east)}": east},
            "plan": {k: j["plan"][k] for k in ("cycleS", "mainGreenS", "crossGreenS", "label", "source")},
        })  # fmt: skip
    # J08 has no position yet: extrapolate 500 m beyond J07 along the J06 -> J07 direction (ASSUMED)
    for i, j in enumerate(out):
        if j["lat"] is None and i + 2 < len(out):
            a, b = out[i + 1], out[i + 2]  # J07, J06
            dlat, dlng = a["lat"] - b["lat"], a["lng"] - b["lng"]
            metres = ((dlat * 111_320) ** 2 + (dlng * 111_320 * 0.893) ** 2) ** 0.5
            f = 500 / metres
            j["lat"], j["lng"] = round(a["lat"] + dlat * f, 6), round(a["lng"] + dlng * f, 6)
            j["positionStatus"] = "ASSUMED"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"order": ORDER, "speedLimitKmh": 50, "speedLimitSource": "ASSUMED", "junctions": out}, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
