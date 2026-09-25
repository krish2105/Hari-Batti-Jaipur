"""Shared loaders for the analytics package.

Everything here reads files that already exist in the repo:
  data/junction_registry.csv          -> junction IDs, approach names, lanes (when filled)
  data/signal_timings.csv             -> real stopwatch timings (EXAMPLE rows are ignored)
  data/processed/*.csv                -> survey counts (Survey, May 2026), aggregates only
  services/sim/assumptions.toml       -> assumed lanes, saturation flow, amber, all-red ...

Nothing is invented: when a value is missing we fall back to assumptions.toml and say so.
data/processed/tmc_clean.csv is local-only (gitignored); TMC_AVAILABLE tells callers if it exists.
"""

import csv
import os
import tomllib
from collections import defaultdict
from functools import cache
from pathlib import Path


def _find_root() -> Path:
    """Repo root: $HARIBATTI_ROOT if set, else two levels above services/ml (editable/source use),
    else the first parent of the working directory that holds data/junction_registry.csv
    (covers a non-editable install inside another service's virtualenv).
    """
    if env := os.environ.get("HARIBATTI_ROOT"):
        return Path(env).resolve()
    here = Path(__file__).resolve().parents[3]
    if (here / "data" / "junction_registry.csv").exists():
        return here
    for parent in (Path.cwd(), *Path.cwd().parents):
        if (parent / "data" / "junction_registry.csv").exists():
            return parent
    return here


ROOT = _find_root()  # repo root
ML_DIR = ROOT / "services" / "ml"
DATA = ROOT / "data"
PROCESSED = DATA / "processed"
REGISTRY_CSV = DATA / "junction_registry.csv"
TIMINGS_CSV = DATA / "signal_timings.csv"
TMC_CSV = PROCESSED / "tmc_clean.csv"
DAY_SUMMARY_CSV = PROCESSED / "junction_day_summary.csv"
PM_PEAK_CSV = PROCESSED / "pm_peak_approach_turns.csv"
HOURLY_CSV = PROCESSED / "hourly_profile_pcu.csv"
ASSUMPTIONS_TOML = ROOT / "services" / "sim" / "assumptions.toml"
REPORTS_DIR = ML_DIR / "reports"

SURVEY_LABEL = "Survey, May 2026"
ASSUMED_TIMING_LABEL = "Assumed timing – demand-proportional (2-phase, free left)"
FIELD_TIMING_LABEL = "Field timing (stopwatch, data/signal_timings.csv)"
TURNS = ("L", "S", "R")
SURVEY_DAY_START_HOUR = 8  # slot 0 = 08:00-08:15; slot 95 = 07:45-08:00 next morning
EXPECTED_IDS = [f"J0{i}" for i in range(1, 9)]

# Corridor (main) road approaches. The other two arms at each junction are cross roads.
_MAIN_J01_J02 = ("B2BYPASS", "SUMER NAGAR")
_MAIN_J03_J08 = ("Mansarover Metro", "Sanganer Stadium")

TMC_AVAILABLE = TMC_CSV.exists()
TMC_MISSING_MSG = (
    f"{TMC_CSV.relative_to(ROOT)} is missing. It is local-only (gitignored, built from the confidential "
    "survey by scripts/process_tmc.py). Build it locally to get AM-peak v/c, hourly flows and the forecaster."
)


# ---------------------------------------------------------------- small helpers


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file into a list of dicts (all values are strings)."""
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def slot_of(hhmm: str) -> int:
    """Clock time "09:15" -> survey slot number (0 = 08:00, 95 = 07:45 next morning)."""
    hour, minute = (int(p) for p in hhmm.split(":"))
    return ((hour - SURVEY_DAY_START_HOUR) % 24) * 4 + minute // 15


def hour_of_slot(slot: int) -> int:
    """Survey slot -> clock hour 0-23 (slot 0-3 -> 8, slot 64-67 -> 0)."""
    return (SURVEY_DAY_START_HOUR + slot // 4) % 24


# ---------------------------------------------------------------- assumptions + registry


@cache
def load_assumptions() -> dict:
    """Parsed services/sim/assumptions.toml (sections: lanes, capacity, timing, geometry ...)."""
    with ASSUMPTIONS_TOML.open("rb") as f:
        return tomllib.load(f)


@cache
def load_registry() -> dict[str, dict]:
    """Registry rows keyed by junction ID, with approaches split into a tuple.

    Fails loudly if the IDs are not exactly J01-J08 (we never invent or rename junctions).
    """
    rows = _read_csv(REGISTRY_CSV)
    out: dict[str, dict] = {}
    for r in rows:
        jid = r["junction_id"].strip()
        out[jid] = {
            "junction_id": jid,
            "junction_name": r["junction_name"].strip(),
            "approaches": tuple(a.strip() for a in r["approaches_used"].split("|") if a.strip()),
            "lanes_raw": (r.get("lanes_per_approach") or "").strip(),
            "signal_type": (r.get("signal_type") or "").strip(),
        }
    if list(out) != EXPECTED_IDS:
        raise ValueError(f"Registry must list exactly {EXPECTED_IDS}, got {list(out)}")
    return out


def junction_ids() -> list[str]:
    """J01..J08 in registry order."""
    return list(load_registry())


def approaches(junction_id: str) -> tuple[str, ...]:
    """Approach names of one junction, exactly as written in the registry."""
    return load_registry()[junction_id]["approaches"]


def main_approaches(junction_id: str) -> tuple[str, str]:
    """The two corridor-road approaches (they share the main green in the 2-phase plan)."""
    if junction_id not in load_registry():
        raise KeyError(f"Unknown junction {junction_id!r}")
    return _MAIN_J01_J02 if junction_id in ("J01", "J02") else _MAIN_J03_J08


def cross_approaches(junction_id: str) -> tuple[str, ...]:
    """The two cross-road approaches (every registry approach that is not on the main road)."""
    main = main_approaches(junction_id)
    return tuple(a for a in approaches(junction_id) if a not in main)


def parse_lanes(raw: str, approach_names: tuple[str, ...]) -> dict[str, int]:
    """Parse lanes_per_approach from the registry.

    "3"                                  -> every approach has 3 lanes
    "Mansarover Metro:3 | Sumer Nagar:2" -> per approach; approaches not listed are left out
    ""                                   -> {} (caller falls back to assumptions.toml)
    """
    raw = (raw or "").strip()
    if not raw:
        return {}
    if raw.isdigit():
        return {a: int(raw) for a in approach_names}
    known = {a.lower(): a for a in approach_names}
    lanes: dict[str, int] = {}
    for part in raw.split("|"):
        name, _, value = part.rpartition(":")
        name = name.strip()
        if name.lower() not in known or not value.strip().isdigit():
            raise ValueError(f"Bad lanes_per_approach entry {part!r}; expected 'Approach Name:3'")
        lanes[known[name.lower()]] = int(value.strip())
    return lanes


def lanes_for(junction_id: str) -> tuple[dict[str, int], dict[str, str]]:
    """Lanes per approach and where each number came from ("registry" or "ASSUMED").

    Registry value wins; otherwise assumptions.toml main_road / cross_road.
    """
    reg = load_registry()[junction_id]
    given = parse_lanes(reg["lanes_raw"], reg["approaches"])
    a_lanes = load_assumptions()["lanes"]
    main = main_approaches(junction_id)
    lanes: dict[str, int] = {}
    source: dict[str, str] = {}
    for name in reg["approaches"]:
        if name in given:
            lanes[name], source[name] = given[name], "registry"
        else:
            key = "main_road" if name in main else "cross_road"
            lanes[name], source[name] = int(a_lanes[key]), "ASSUMED"
    return lanes, source


# ---------------------------------------------------------------- processed survey aggregates


@cache
def load_day_summary() -> dict[tuple[str, str], dict]:
    """junction_day_summary.csv keyed by (junction_id, survey_date)."""
    return {(r["junction_id"], r["survey_date"]): r for r in _read_csv(DAY_SUMMARY_CSV)}


def survey_dates(junction_id: str) -> list[str]:
    """Dates with survey counts for one junction (J01/J02: 11 May only)."""
    return sorted(d for (j, d) in load_day_summary() if j == junction_id)


def load_pm_peak(date: str) -> dict[str, dict[str, dict[str, float]]]:
    """PM-peak-hour PCU/h per junction -> approach -> turn (L/S/R). Survey, May 2026."""
    out: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for r in _read_csv(PM_PEAK_CSV):
        if r["survey_date"] == date:
            out[r["junction_id"]][r["from_approach"]] = {t: float(r[t]) for t in TURNS}
    return dict(out)


def load_field_timings() -> dict[str, list[dict[str, str]]]:
    """Real stopwatch rows grouped by junction. Rows whose notes contain EXAMPLE are dropped."""
    rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in _read_csv(TIMINGS_CSV):
        if "EXAMPLE" in (r.get("notes") or "").upper():
            continue
        jid = (r.get("junction_id") or "").strip()
        if jid:
            rows[jid].append(r)
    return dict(rows)


# ---------------------------------------------------------------- tmc_clean (local only)


@cache
def load_tmc() -> tuple[dict, ...]:
    """Typed rows of tmc_clean.csv: junction_id, survey_date, movement, from/to approach, turn,
    slot, total_veh, total_pcu. Only the columns the analytics need are kept.

    Raises FileNotFoundError with a clear message when the local-only file is missing.
    """
    if not TMC_CSV.exists():
        raise FileNotFoundError(TMC_MISSING_MSG)
    return tuple(
        {
            "junction_id": r["junction_id"],
            "survey_date": r["survey_date"],
            "movement": int(r["movement"]),
            "from_approach": r["from_approach"],
            "to_approach": r["to_approach"],
            "turn": r["turn"],
            "slot": int(r["slot"]),
            "total_veh": float(r["total_veh"]),
            "total_pcu": float(r["total_pcu"]),
        }
        for r in _read_csv(TMC_CSV)
    )


def slot_approach_pcu(date: str, turns: tuple[str, ...] = TURNS) -> dict[tuple[str, str, int], float]:
    """{(junction, approach, slot): PCU in that 15 min} summed over the given turns."""
    out: dict[tuple[str, str, int], float] = defaultdict(float)
    for r in load_tmc():
        if r["survey_date"] == date and r["turn"] in turns:
            out[(r["junction_id"], r["from_approach"], r["slot"])] += r["total_pcu"]
    return dict(out)


def hourly_approach_pcu(date: str, turns: tuple[str, ...] = TURNS) -> dict[tuple[str, str, int], float]:
    """{(junction, approach, clock hour 0-23): PCU/h} from tmc_clean (Survey, May 2026).

    Each hour is the sum of its four 15-min slots. By default all turns are counted; pass
    turns=("S", "R") for the flow the 2-phase free-left plan must serve (left turns run free).
    """
    out: dict[tuple[str, str, int], float] = defaultdict(float)
    for (jid, appr, slot), pcu in slot_approach_pcu(date, turns).items():
        out[(jid, appr, hour_of_slot(slot))] += pcu
    return dict(out)
