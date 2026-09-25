"""Build data/junctions.geojson from data/junction_registry.csv (J01–J08, Mansarovar corridor).

- Junction IDs, names and approach names come only from the registry. Nothing is invented.
- If a row has no lat/lng yet, it gets a PLACEHOLDER point on a straight line between rough
  Mansarovar Metro and Sanganer Stadium end points, in ID order, flagged `verify: true`.
  These placeholders are NOT real positions; fill lat/lng in the registry and re-run.
- No traffic counts go into this file.

Run: uv run --no-project --python 3.12 python scripts/build_junctions_geojson.py
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/junction_registry.csv"
OUT = ROOT / "data/junctions.geojson"

# Rough corridor end points used ONLY to spread placeholder markers. Verify on Google Maps.
PLACEHOLDER_START = (26.8790, 75.7480)  # near Mansarovar Metro (approx.)
PLACEHOLDER_END = (26.8300, 75.7900)  # near Sanganer Stadium (approx.)

CONTROL_TYPES = {"AI_ITMS", "FIXED", "FLASHING"}


def _float_or_none(value: str) -> float | None:
    """Turn a CSV cell into a float, or None when it is blank."""
    value = (value or "").strip()
    return float(value) if value else None


def build(registry_path: Path = REGISTRY) -> dict:
    """Read the registry and return a GeoJSON FeatureCollection (one Point per junction)."""
    with registry_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    features = []
    n = len(rows)
    for i, row in enumerate(rows):
        lat, lng = _float_or_none(row["lat"]), _float_or_none(row["lng"])
        placeholder = lat is None or lng is None
        if placeholder:
            t = i / (n - 1) if n > 1 else 0.0
            lat = PLACEHOLDER_START[0] + t * (PLACEHOLDER_END[0] - PLACEHOLDER_START[0])
            lng = PLACEHOLDER_START[1] + t * (PLACEHOLDER_END[1] - PLACEHOLDER_START[1])

        signal_type = row["signal_type"].strip().upper()
        features.append(
            {
                "type": "Feature",
                "id": row["junction_id"],
                # GeoJSON order is [longitude, latitude].
                "geometry": {"type": "Point", "coordinates": [round(lng, 6), round(lat, 6)]},
                "properties": {
                    "id": row["junction_id"],
                    "name": row["junction_name"],
                    "tmc_code": row["tmc_code"] or None,
                    "approaches": [a.strip() for a in row["approaches_used"].split("|") if a.strip()],
                    "signal_type": signal_type or None,
                    "controlType": signal_type if signal_type in CONTROL_TYPES else "UNKNOWN",
                    "coord_status": "PLACEHOLDER_VERIFY" if placeholder else "REGISTRY",
                    "verify": placeholder,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "name": "HariBatti Mansarovar corridor pilot junctions (J01–J08)",
        "source": "data/junction_registry.csv",
        "note": "Points with verify=true are placeholders, not real positions.",
        "features": features,
    }


def main() -> None:
    """Write the GeoJSON file and print a short summary."""
    fc = build()
    OUT.write_text(json.dumps(fc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    todo = [f["id"] for f in fc["features"] if f["properties"]["verify"]]
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(fc['features'])} junctions; placeholders to verify: {todo}")


if __name__ == "__main__":
    main()
