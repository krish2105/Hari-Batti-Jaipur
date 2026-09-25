"""Load the pilot junctions (J01-J08) from data/junction_registry.csv.

Junction IDs, names and approach names come ONLY from the registry. Nothing is invented here.
"""

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import REGISTRY_CSV

EXPECTED_IDS = [f"J0{i}" for i in range(1, 9)]


@dataclass(frozen=True)
class Junction:
    """One registry row, with blanks turned into None."""

    id: str
    name: str
    tmc_code: str | None
    approaches: tuple[str, ...]
    lat: float | None
    lng: float | None
    lanes_raw: str  # lanes_per_approach as written (may be blank)
    signal_type: str
    extra: dict = field(default_factory=dict, compare=False)

    @property
    def has_coords(self) -> bool:
        return self.lat is not None and self.lng is not None


def _float_or_none(value: str | None) -> float | None:
    value = (value or "").strip()
    return float(value) if value else None


def slug(text: str) -> str:
    """Make an ID-safe name: 'Mansarover Metro' -> 'mansarover-metro'."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def load_registry(path: Path = REGISTRY_CSV) -> list[Junction]:
    """Read every registry row. Fails loudly if the IDs are not exactly J01-J08."""
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    junctions = [
        Junction(
            id=r["junction_id"].strip(),
            name=r["junction_name"].strip(),
            tmc_code=(r.get("tmc_code") or "").strip() or None,
            approaches=tuple(a.strip() for a in r["approaches_used"].split("|") if a.strip()),
            lat=_float_or_none(r.get("lat")),
            lng=_float_or_none(r.get("lng")),
            lanes_raw=(r.get("lanes_per_approach") or "").strip(),
            signal_type=(r.get("signal_type") or "").strip(),
        )
        for r in rows
    ]
    ids = [j.id for j in junctions]
    if ids != EXPECTED_IDS:
        raise ValueError(f"Registry must list exactly {EXPECTED_IDS}, got {ids}")
    return junctions


def all_coords_present(junctions: list[Junction]) -> bool:
    """True only when every junction has lat and lng (then the OSM network is used)."""
    return all(j.has_coords for j in junctions)


def parse_lanes(raw: str, approaches: tuple[str, ...]) -> dict[str, int]:
    """Parse lanes_per_approach.

    Accepted formats (see data/README.md):
      "3"                                -> every approach has 3 lanes
      "Mansarover Metro:3 | Sumer Nagar:2" -> per approach; approaches not listed are left out
    Returns {} when blank, so the caller falls back to assumptions.toml.
    """
    raw = (raw or "").strip()
    if not raw:
        return {}
    if raw.isdigit():
        return {a: int(raw) for a in approaches}
    lanes: dict[str, int] = {}
    known = {a.lower(): a for a in approaches}
    for part in raw.split("|"):
        name, _, value = part.rpartition(":")
        name = name.strip()
        if name.lower() not in known or not value.strip().isdigit():
            raise ValueError(f"Bad lanes_per_approach entry {part!r}; expected 'Approach Name:3'")
        lanes[known[name.lower()]] = int(value.strip())
    return lanes
