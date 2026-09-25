"""Survey demand from data/processed/tmc_clean.csv — the ONLY source of traffic volumes.

Counts are used exactly as surveyed ("Survey, May 2026"). Nothing is invented or sampled here.
"""

import csv
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .config import TMC_CSV

SLOTS_PER_DAY = 96

# Survey class columns -> simulator vehicle type (see vtypes in build.py).
CLASS_TO_VTYPE = {
    "car_taxi_auto_pickup": "car",
    "two_wheeler": "two_wheeler",
    "tractor_lcv_minibus": "lcv",
    "axle_truck_bus": "bus_truck",
    "truck_trailer_mav": "trailer",
    "cycle": "slow",
    "cycle_rickshaw": "slow",
    "hand_cart": "slow",
    "horse_drawn": "slow",
    "bullock_cart": "slow",
}


@dataclass(frozen=True)
class Movement:
    """One of the 12 turning movements at a junction."""

    junction_id: str
    from_approach: str
    to_approach: str
    turn: str  # "L", "S" or "R" as surveyed


@dataclass
class DayCounts:
    """All survey counts for one date."""

    date: str
    # movement -> 96 vehicle counts (one per 15-min slot, slot 0 = 08:00-08:15)
    veh: dict[Movement, list[float]]
    # movement -> 96 PCU counts
    pcu: dict[Movement, list[float]]
    # vehicle type -> total vehicles that day (for the vehicle mix)
    class_totals: dict[str, float]

    @property
    def junction_ids(self) -> list[str]:
        return sorted({m.junction_id for m in self.veh})

    def hourly(self, movement: Movement) -> list[float]:
        """24 hourly vehicle counts for a movement (hour 0 = 08:00-09:00)."""
        s = self.veh[movement]
        return [sum(s[h * 4 : h * 4 + 4]) for h in range(24)]


@lru_cache(maxsize=4)
def _read_rows(path: Path) -> tuple[dict, ...]:
    with path.open(newline="", encoding="utf-8") as f:
        return tuple(csv.DictReader(f))


def load_day(date: str, path: Path = TMC_CSV) -> DayCounts:
    """Load one survey date. Raises if the date is not in the file."""
    veh: dict[Movement, list[float]] = defaultdict(lambda: [0.0] * SLOTS_PER_DAY)
    pcu: dict[Movement, list[float]] = defaultdict(lambda: [0.0] * SLOTS_PER_DAY)
    class_totals: dict[str, float] = defaultdict(float)
    found = False
    for r in _read_rows(path):
        if r["survey_date"] != date:
            continue
        found = True
        m = Movement(r["junction_id"], r["from_approach"], r["to_approach"], r["turn"])
        slot = int(r["slot"])
        veh[m][slot] += float(r["total_veh"])
        pcu[m][slot] += float(r["total_pcu"])
        for col, vtype in CLASS_TO_VTYPE.items():
            class_totals[vtype] += float(r[col] or 0)
    if not found:
        raise ValueError(f"No survey rows for {date} in {path}")
    return DayCounts(date, dict(veh), dict(pcu), dict(class_totals))


def vehicle_mix(day: DayCounts) -> dict[str, float]:
    """Share of each vehicle type in the day's survey counts (sums to 1)."""
    total = sum(day.class_totals.values())
    return {k: v / total for k, v in sorted(day.class_totals.items())}
