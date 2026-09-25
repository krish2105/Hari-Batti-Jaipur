"""Data guard-rails: junction IDs, the generated GeoJSON, and the processed survey CSVs.

data/processed/*.csv is the ONLY source of traffic volumes. These tests lock in the row counts
and junction IDs documented in data/README.md so nothing silently changes or gets invented.
"""

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
EXPECTED_IDS = [f"J0{i}" for i in range(1, 9)]

# Rows documented in data/README.md.
PROCESSED_ROWS = {
    "tmc_clean.csv": 16_128,
    "junction_day_summary.csv": 14,
    "pm_peak_approach_turns.csv": 56,
    "hourly_profile_pcu.csv": 336,
}


def _rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_builder():
    """Import scripts/build_junctions_geojson.py without making scripts/ a package."""
    spec = importlib.util.spec_from_file_location("build_geojson", ROOT / "scripts/build_junctions_geojson.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_registry_has_exactly_j01_to_j08() -> None:
    ids = [r["junction_id"] for r in _rows(DATA / "junction_registry.csv")]
    assert ids == EXPECTED_IDS


def test_geojson_file_matches_registry() -> None:
    on_disk = json.loads((DATA / "junctions.geojson").read_text(encoding="utf-8"))
    assert on_disk == _load_builder().build(), "junctions.geojson is stale: re-run the build script"
    assert [f["id"] for f in on_disk["features"]] == EXPECTED_IDS


def test_placeholders_are_flagged() -> None:
    reg = {r["junction_id"]: r for r in _rows(DATA / "junction_registry.csv")}
    for f in _load_builder().build()["features"]:
        blank = not (reg[f["id"]]["lat"].strip() and reg[f["id"]]["lng"].strip())
        assert f["properties"]["verify"] is blank
        assert f["properties"]["coord_status"] == ("PLACEHOLDER_VERIFY" if blank else "REGISTRY")


def test_geojson_has_no_counts() -> None:
    props = _load_builder().build()["features"][0]["properties"]
    assert not any(k in props for k in ("total_veh", "total_pcu", "pcu", "volume"))


def test_processed_csvs_row_counts_and_ids() -> None:
    for name, expected in PROCESSED_ROWS.items():
        path = DATA / "processed" / name
        if name == "tmc_clean.csv" and not path.exists():
            continue  # confidential, local only (not in the public repo)
        rows = _rows(path)
        assert len(rows) == expected, name
        assert {r["junction_id"] for r in rows} <= set(EXPECTED_IDS), name


def test_summary_matches_documented_headline() -> None:
    # docs/05-data-analysis.md: J01 SFS RIICO, Mon 11 May 2026 = 176,546 vehicles in 24 h.
    rows = _rows(DATA / "processed/junction_day_summary.csv")
    j01 = next(r for r in rows if r["junction_id"] == "J01" and r["survey_date"].startswith("2026-05-11"))
    assert int(float(j01["total_veh"])) == 176_546
