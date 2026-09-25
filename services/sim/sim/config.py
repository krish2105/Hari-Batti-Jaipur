"""Paths, environment settings and fixed facts used by the simulator.

Environment values come from the repo .env (the Makefile exports it). Defaults match .env.example.
"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

SIM_DIR = Path(__file__).resolve().parents[1]  # services/sim
ROOT = SIM_DIR.parents[1]  # repo root
DATA = ROOT / "data"
REGISTRY_CSV = DATA / "junction_registry.csv"
TIMINGS_CSV = DATA / "signal_timings.csv"
TMC_CSV = DATA / "processed" / "tmc_clean.csv"
PM_PEAK_CSV = DATA / "processed" / "pm_peak_approach_turns.csv"
OSM_FILE = DATA / "osm" / "mansarovar.osm"
CANDIDATES_CSV = DATA / "junction_coords_candidates.csv"
BUILD_DIR = SIM_DIR / "build"
REPORTS_DIR = SIM_DIR / "reports"
ASSUMPTIONS_TOML = SIM_DIR / "assumptions.toml"

# The survey runs 08:00 -> 08:00 next day in 96 x 15-min slots. Sim time 0 s = 08:00 IST.
IST = ZoneInfo("Asia/Kolkata")
SURVEY_DAY_START_HOUR = 8
SLOT_S = 900
DAY_S = 24 * 3600
CALIBRATION_DATE = "2026-05-11"  # Monday: demand + calibration
VALIDATION_DATE = "2026-05-12"  # Tuesday: independent check (J03-J08 only)

REDIS_CHANNEL = "signals"

GEOMETRY_LABELS = {
    "SCHEMATIC": "Schematic network – coordinates pending",
    "OSM": "OSM network (coordinates from data/junction_registry.csv)",
    "OSM_CANDIDATE": "OSM network – CANDIDATE coords, unverified (test only)",
}


def redis_url() -> str:
    """Redis URL from .env, else the Docker default on host port 6380."""
    if url := os.environ.get("REDIS_URL"):
        return url
    return f"redis://localhost:{os.environ.get('REDIS_PORT', '6380')}/0"


@dataclass(frozen=True)
class Assumptions:
    """All assumed values from services/sim/assumptions.toml, as a plain dict per section."""

    raw: dict

    def __getitem__(self, key: str) -> dict:
        return self.raw[key]


def load_assumptions(path: Path = ASSUMPTIONS_TOML) -> Assumptions:
    """Read assumptions.toml."""
    with path.open("rb") as f:
        return Assumptions(tomllib.load(f))
