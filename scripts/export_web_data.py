"""Export AGGREGATES for the public website -> apps/web/public/data/site.json (committed).

The website is public, so it gets only aggregates: daily totals, peak hours, hourly PCU per
junction, daily Health Score summaries and signal plans. Never raw survey rows.
Needs the local data/processed/tmc_clean.csv for the Health summaries.
Run: cd services/ml && uv run python ../../scripts/export_web_data.py
"""

import csv
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from ml import capacity, metrics

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "apps" / "web" / "public" / "data" / "site.json"
DATE = "2026-05-11"
MAIN = {"J01": ("B2BYPASS", "SUMER NAGAR"), "J02": ("B2BYPASS", "SUMER NAGAR")}


def rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def positions() -> dict[str, dict]:
    """Registry lat/lng, else rank-1 OSM candidate (unverified), else pending (no point)."""
    pos = {}
    for r in rows(DATA / "junction_registry.csv"):
        if r["lat"].strip() and r["lng"].strip():
            pos[r["junction_id"]] = {"lat": float(r["lat"]), "lng": float(r["lng"]), "status": "REGISTRY"}
    for r in rows(DATA / "junction_coords_candidates.csv"):
        jid = r["junction_id"]
        if jid not in pos and r["rank"] == "1" and r["candidate_lat"]:
            pos[jid] = {"lat": float(r["candidate_lat"]), "lng": float(r["candidate_lng"]), "status": "CANDIDATE",
                        "confidence": r["confidence"], "alsoMatches": r["also_matches"] or None}
    return pos


# Survey vehicle classes -> our 3D models. PCU factors are the survey's own, recovered exactly
# (R^2 = 1.0) by least squares of total_pcu on the class counts; only the factors are published.
CLASSES = [
    ("two_wheeler", "Two-wheelers", ["scooter", "motorcycle"]),
    ("car_taxi_auto_pickup", "Cars, taxis, autos, pickups", ["hatchback", "sedan", "suv", "auto_rickshaw", "e_rickshaw"]),
    ("tractor_lcv_minibus", "Tractors, LCVs, minibuses", ["lcv_tempo", "mini_bus", "tractor"]),
    ("axle_truck_bus", "Two-axle trucks and buses", ["city_bus", "truck"]),
    ("truck_trailer_mav", "Trailers and multi-axle trucks", ["truck"]),
    ("cycle", "Bicycles", ["bicycle"]),
    ("cycle_rickshaw", "Cycle rickshaws", ["cycle_rickshaw"]),
    ("hand_cart", "Hand carts", ["hand_cart"]),
    ("horse_drawn", "Horse-drawn (to verify: may be e-rickshaws or carts)", []),
    ("bullock_cart", "Bullock carts", []),
]


def vehicle_classes() -> list[dict]:
    """Corridor totals per class (both survey days) and the survey's PCU factor per class."""
    import numpy as np

    tmc = DATA / "processed" / "tmc_clean.csv"
    keys = [c[0] for c in CLASSES]
    rows_ = rows(tmc)
    X = np.array([[float(r[k] or 0) for k in keys] for r in rows_])
    y = np.array([float(r["total_pcu"]) for r in rows_])
    factors, *_ = np.linalg.lstsq(X, y, rcond=None)
    fit_r2 = 1 - ((y - X @ factors) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    totals = X.sum(axis=0)

    out = []
    for (key, label, models), f, n in zip(CLASSES, factors, totals, strict=True):
        out.append({"key": key, "label": label, "pcu": round(float(f), 2), "vehicles": int(n),
                    "share": round(float(n / totals.sum()), 4), "models": models})
    return [{"fitR2": round(float(fit_r2), 6)}, *out]


def main() -> None:
    reg = rows(DATA / "junction_registry.csv")
    summary = defaultdict(dict)
    for r in rows(DATA / "processed" / "junction_day_summary.csv"):
        summary[r["junction_id"]][r["survey_date"]] = {
            "totalVeh": int(float(r["total_veh"])), "totalPcu": round(float(r["total_pcu"])),
            "twoWheelerPct": float(r["two_wheeler_pct"]),
            "amPeak": r["am_peak_start"], "amPeakPcu": round(float(r["am_peak_pcu_hr"])),
            "pmPeak": r["pm_peak_start"], "pmPeakPcu": round(float(r["pm_peak_pcu_hr"])),
        }
    hourly = defaultdict(lambda: [0] * 24)
    for r in rows(DATA / "processed" / "hourly_profile_pcu.csv"):
        if r["survey_date"] == DATE:
            hourly[r["junction_id"]][int(r["hour"])] = round(float(r["total_pcu"]))
    pm = defaultdict(dict)
    for r in rows(DATA / "processed" / "pm_peak_approach_turns.csv"):
        if r["survey_date"] == DATE:
            pm[r["junction_id"]][r["from_approach"]] = round(float(r["approach_pcu_hr"]))

    ahs = capacity.approach_hours(DATE)
    health: dict[str, list[tuple[int, float, float]]] = defaultdict(list)
    for jid in {a.junction_id for a in ahs}:
        timing = capacity.junction_timing(jid, DATE)
        for h in range(24):
            group = [a for a in ahs if a.junction_id == jid and a.hour == h]
            m = metrics.junction_metrics(metrics.assume_pedestrians(group, timing["green_s"]))
            health[jid].append((h, m["health"], m["red_wait_s"]))
    vc = capacity.vc_table(DATE)

    pos = positions()
    junctions = []
    for r in reg:
        jid = r["junction_id"]
        timing = capacity.junction_timing(jid, DATE)
        main = MAIN.get(jid, ("Mansarover Metro", "Sanganer Stadium"))
        hs = health[jid]
        worst = min(hs, key=lambda x: x[1])
        junctions.append({
            "id": jid, "name": r["junction_name"].replace(" Junction", ""),
            "position": pos.get(jid, {"lat": None, "lng": None, "status": "PENDING"}),
            "approaches": [{"name": a.strip(), "main": a.strip() in main, "pmPeakPcu": pm[jid].get(a.strip())}
                           for a in r["approaches_used"].split("|")],
            "survey": summary[jid], "hourlyPcu": hourly[jid],
            "plan": {"cycleS": timing["cycle_s"], "mainGreenS": timing["green_s"][main[0]],
                     "crossGreenS": min(g for n, g in timing["green_s"].items() if n not in main),
                     "label": timing["label"], "source": timing["source"], "oversaturated": timing["oversaturated"]},
            "health": {"avg": round(sum(x[1] for x in hs) / len(hs), 1), "worst": worst[1],
                       "worstHour": f"{(worst[0] + 8) % 24:02d}:00",
                       "avgRedWaitS": round(sum(x[2] for x in hs) / len(hs), 1)},
            "vcOver09": sum(1 for v in vc if v["junction_id"] == jid and v["vc"] > 0.9),
        })
    corridor = {
        "totalVeh": sum(j["survey"][DATE]["totalVeh"] for j in junctions),
        "junctions": len(junctions), "junctionDays": sum(len(j["survey"]) for j in junctions),
        "twoWheelerPctRange": [min(j["survey"][DATE]["twoWheelerPct"] for j in junctions),
                               max(j["survey"][DATE]["twoWheelerPct"] for j in junctions)],
        "vcOver09": sum(j["vcOver09"] for j in junctions), "vcRows": len(vc),
        "busiestPmPeak": max(junctions, key=lambda j: j["survey"][DATE]["pmPeakPcu"])["id"],
    }
    classes = vehicle_classes()
    out = {
        "generated": datetime.now(UTC).strftime("%Y-%m-%d"),
        "vehicleClasses": {"pcuFitR2": classes[0]["fitR2"], "classes": classes[1:],
                           "note": "PCU factors are the survey's own (recovered from its PCU totals); counts are both survey days, all junctions"},
        "labels": {"survey": "Survey, May 2026", "timing": "Assumed timing – demand-proportional (2-phase, free left)",
                   "health": "Survey counts + assumed timing", "position": "Approximate, unverified OpenStreetMap match"},
        "corridor": corridor, "junctions": junctions,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB): {corridor}")


if __name__ == "__main__":
    main()
