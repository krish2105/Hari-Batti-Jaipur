"""Export model RESULTS for the public website -> apps/web/public/data/results.json (committed).

Reads only the committed result files (all aggregates, each with its source label):
  services/sim/reports/calibration_best.json, calibration_trials.csv, calibration_diagnostics.json
  services/ml/reports/controllers.json, timespace.json, forecast.json, anomalies.json
  services/cv/reports/cv_eval.json
A missing file becomes null, and the website shows that result as pending. No survey rows are read.
Run from the repo root: python3 scripts/export_results.py
"""

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps" / "web" / "public" / "data" / "results.json"


def load(rel: str):
    p = ROOT / rel
    if not p.exists():
        return None
    if p.suffix == ".csv":
        with p.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    return json.loads(p.read_text(encoding="utf-8"))


def calibration() -> dict | None:
    best = load("services/sim/reports/calibration_best.json")
    if not best:
        return None
    trials = load("services/sim/reports/calibration_trials.csv") or []
    diag = load("services/sim/reports/calibration_diagnostics.json") or {}
    return {
        "source": "SIM",
        "target": 0.85,
        "unservedTarget": 0.05,
        "calibration": round(best["calibration_geh_share"], 4),
        "validation": best.get("validation_geh_share"),
        "unserved": best.get("unserved_share"),
        "trialsRun": len(trials),
        "trials": [
            {"trial": int(t["trial"]), "cal": round(float(t["calibration_geh_share"]), 4), "val": round(float(t["validation_geh_share"]), 4),
             "unserved": round(float(t["unserved_share"]), 4), "lanes": f"{t['main_lanes']}/{t['cross_lanes']}"}
            for t in trials
        ],  # fmt: skip
        "variants": [
            {"id": v["id"], "label": v["label"], "cal": v["calibration_geh_share"], "val": v["validation_geh_share"], "unserved": v["unserved_share"]}
            for v in diag.get("variants", [])
        ],  # fmt: skip
        "saturationPcu": (diag.get("saturation", {}).get("survey mix, sublane on") or {}).get("pcu_per_green_h_per_lane"),
    }


def optimisation() -> dict | None:
    c = load("services/ml/reports/controllers.json")
    ts = load("services/ml/reports/timespace.json")
    if not c:
        return None
    keep = ("travelTimeS", "waitingTimeS", "stops", "queueVeh", "throughputVeh", "co2PerTripG", "unservedVeh")
    return {
        "source": "SIM",
        "evalDay": c["evalDay"],
        "window": c["window"],
        "seeds": len(c["seeds"]),
        "controllers": [{"id": r["id"], "label": r["label"], "kind": r["kind"], **{k: r[k] for k in keep}} for r in c["controllers"]],
        "greenWave": None if not ts else {k: ts[k] for k in ("cycleS", "speedKmh", "spacingM", "bandwidthS", "bandwidthZeroOffsetsS", "junctions")},
    }


def forecast() -> dict | None:
    f = load("services/ml/reports/forecast.json")
    a = load("services/ml/reports/anomalies.json")
    if not f:
        return None
    pick = lambda b: {k: b[k] for k in ("data", "train", "test", "nTrain", "nTest", "models")}  # noqa: E731
    return {
        "real": pick(f["real"]),
        "sim": pick(f["sim"]),
        "conformal": f["conformal"],
        "phaseChange": f.get("phaseChange"),
        "dataQuality": f.get("dataQuality"),
        "anomalies": None if not a else {"injected": a["injected"], "recallByKind": a.get("recallByKind")},
    }


def vision() -> dict | None:
    v = load("services/cv/reports/cv_eval.json")
    if not v or "models" not in v:
        return None
    return {k: v.get(k) for k in ("dataset", "images", "boxes", "models", "classes", "speedMs", "videos")}


def main() -> None:
    out = {
        "generated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
        "calibration": calibration(),
        "optimisation": optimisation(),
        "forecast": forecast(),
        "vision": vision(),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.1f} KB): " + ", ".join(k for k, v in out.items() if v and k != "generated"))


if __name__ == "__main__":
    main()
