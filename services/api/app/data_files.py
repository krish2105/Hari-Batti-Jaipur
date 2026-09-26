"""Read the project's data files (the source of truth) for the API.

- Junction IDs, names, approaches: data/junction_registry.csv
- Positions: registry lat/lng; else unverified OSM candidates (data/junction_coords_candidates.csv);
  else PENDING (no point drawn). Every position carries its status.
- Survey aggregates ("Survey, May 2026"): data/processed/junction_day_summary.csv etc.
- Approach sides (W/N/E/S) come from the survey's own L/S/R labels (tmc_clean.csv, local only).
"""

import csv
import re
import tomllib
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from .config import ROOT

DATA = ROOT / "data"
REGISTRY = DATA / "junction_registry.csv"
CANDIDATES = DATA / "junction_coords_candidates.csv"
SUMMARY = DATA / "processed" / "junction_day_summary.csv"
HOURLY = DATA / "processed" / "hourly_profile_pcu.csv"
PM_PEAK = DATA / "processed" / "pm_peak_approach_turns.csv"
TMC = DATA / "processed" / "tmc_clean.csv"
TIMINGS = DATA / "signal_timings.csv"
ASSUMPTIONS = ROOT / "services" / "sim" / "assumptions.toml"
SURVEY_LABEL = "Survey, May 2026"
MAIN = {"J01": ("B2BYPASS", "SUMER NAGAR"), "J02": ("B2BYPASS", "SUMER NAGAR")}
DEFAULT_MAIN = ("Mansarover Metro", "Sanganer Stadium")
TURN_TARGET = {"W": {"L": "N", "S": "E", "R": "S"}}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache
def assumptions() -> dict:
    with ASSUMPTIONS.open("rb") as f:
        return tomllib.load(f)


@lru_cache
def registry() -> list[dict]:
    rows = _rows(REGISTRY)
    ids = [r["junction_id"] for r in rows]
    if ids != [f"J0{i}" for i in range(1, 9)]:
        raise ValueError(f"registry must be J01-J08, got {ids}")
    return rows


def main_approaches(junction_id: str) -> tuple[str, str]:
    return MAIN.get(junction_id, DEFAULT_MAIN)


def parse_lanes(raw: str, names: list[str]) -> dict[str, int]:
    """'3' or 'Name:3 | Other:2' -> lanes per approach; {} when blank."""
    raw = (raw or "").strip()
    if not raw:
        return {}
    if raw.isdigit():
        return dict.fromkeys(names, int(raw))
    out = {}
    for part in raw.split("|"):
        name, _, n = part.rpartition(":")
        if name.strip() in names and n.strip().isdigit():
            out[name.strip()] = int(n)
    return out


@lru_cache
def sides() -> dict[str, dict[str, str]]:
    """junction -> approach -> side, from the survey's own turn labels (needs tmc_clean.csv)."""
    if not TMC.exists():
        return {}
    moves: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    with TMC.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            moves[r["junction_id"]].add((r["from_approach"], r["to_approach"], r["turn"]))
    out: dict[str, dict[str, str]] = {}
    for jid, ms in moves.items():
        west = main_approaches(jid)[0]
        side = {west: "W"}
        for frm, to, turn in ms:
            if frm == west:
                side[to] = TURN_TARGET["W"][turn]
        out[jid] = side
    return out


@lru_cache
def positions() -> dict[str, dict]:
    """Best-known position per junction, always with a status label."""
    pos: dict[str, dict] = {}
    for r in registry():
        if r["lat"].strip() and r["lng"].strip():
            pos[r["junction_id"]] = {
                "lat": float(r["lat"]),
                "lng": float(r["lng"]),
                "status": "REGISTRY",
                "note": "From data/junction_registry.csv",
            }
    if CANDIDATES.exists():
        for r in _rows(CANDIDATES):
            jid = r["junction_id"]
            if jid in pos or r["rank"] != "1" or not r["candidate_lat"]:
                continue
            dup = f"; same point also proposed for {r['also_matches']}" if r.get("also_matches") else ""
            pos[jid] = {
                "lat": float(r["candidate_lat"]),
                "lng": float(r["candidate_lng"]),
                "status": "CANDIDATE",
                "confidence": r["confidence"],
                "note": f"Unverified OpenStreetMap candidate ({r['confidence']}): {r['evidence']}{dup}",
            }
    # No registry value and no candidate: do not draw a guessed point on any map.
    for r in registry():
        pos.setdefault(
            r["junction_id"],
            {
                "lat": None,
                "lng": None,
                "status": "PENDING",
                "note": "Location pending — add lat/lng to data/junction_registry.csv",
            },
        )
    return pos


@lru_cache
def survey_summary() -> dict[str, list[dict]]:
    """Daily totals and peaks per junction (aggregates only)."""
    out: dict[str, list[dict]] = defaultdict(list)
    for r in _rows(SUMMARY):
        out[r["junction_id"]].append(
            {
                "surveyDate": r["survey_date"],
                "totalVeh": int(float(r["total_veh"])),
                "totalPcu": round(float(r["total_pcu"])),
                "twoWheelerPct": float(r["two_wheeler_pct"]),
                "amPeakStart": r["am_peak_start"],
                "amPeakPcuHr": round(float(r["am_peak_pcu_hr"])),
                "pmPeakStart": r["pm_peak_start"],
                "pmPeakPcuHr": round(float(r["pm_peak_pcu_hr"])),
                "source": "SURVEY",
                "sourceLabel": SURVEY_LABEL,
            }
        )
    return dict(out)


@lru_cache
def hourly_profile() -> dict[str, dict[str, list[float]]]:
    """junction -> date -> 24 hourly PCU values indexed by clock hour (index 8 = 08:00-09:00)."""
    out: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0] * 24))
    for r in _rows(HOURLY):
        out[r["junction_id"]][r["survey_date"]][int(r["hour"])] = float(r["total_pcu"])
    return {j: dict(d) for j, d in out.items()}


@lru_cache
def pm_peak(date: str = "2026-05-11") -> dict[str, dict[str, dict[str, float]]]:
    out: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for r in _rows(PM_PEAK):
        if r["survey_date"] == date:
            out[r["junction_id"]][r["from_approach"]] = {t: float(r[t]) for t in "LSR"}
    return dict(out)


def lanes_for(junction_id: str) -> tuple[dict[str, int], str]:
    """Lanes per approach: registry when filled, else assumptions.toml. Returns (lanes, source)."""
    r = next(x for x in registry() if x["junction_id"] == junction_id)
    names = [a.strip() for a in r["approaches_used"].split("|")]
    given = parse_lanes(r.get("lanes_per_approach", ""), names)
    a = assumptions()["lanes"]
    main = main_approaches(junction_id)
    lanes = {n: given.get(n, a["main_road"] if n in main else a["cross_road"]) for n in names}
    return lanes, ("registry" if len(given) == len(names) else "ASSUMED")


def field_timing_junctions() -> set[str]:
    """Junctions with real (non-EXAMPLE) stopwatch rows."""
    return {r["junction_id"] for r in _rows(TIMINGS) if "EXAMPLE" not in (r.get("notes") or "").upper()}
