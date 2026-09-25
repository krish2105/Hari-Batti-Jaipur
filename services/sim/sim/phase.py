"""Turn a SUMO signal program into per-approach PhaseState messages (pure logic, no SUMO needed).

Approach colour = the colour of its straight-ahead movement (free left turns stay green always,
so they would hide the real signal). secondsRemaining = time until that colour changes, walking
forward through the fixed program.
"""

from dataclasses import dataclass
from datetime import datetime

COLOUR_OF = {"G": "GREEN", "g": "GREEN", "y": "AMBER", "Y": "AMBER", "r": "RED", "R": "RED", "s": "RED"}


@dataclass(frozen=True)
class ApproachLinks:
    junction_id: str
    approach_id: str  # e.g. "J04-durgapur"
    approach_name: str
    link_indices: tuple[int, ...]  # the links whose colour we report (straight, else right, else left)


def approach_colour(state: str, links: tuple[int, ...]) -> str:
    """Colour of an approach from a SUMO state string. Green if any reported link is green."""
    colours = {COLOUR_OF.get(state[i], "RED") for i in links}
    for c in ("GREEN", "AMBER"):
        if c in colours:
            return c
    return "RED"


def seconds_until_change(
    phases: list[tuple[int, str]], index: int, remaining_in_phase: float, links: tuple[int, ...]
) -> float:
    """Seconds until this approach's colour changes.

    phases: [(duration_s, state)], index: current phase, remaining_in_phase: time left in it.
    Walks forward (wrapping round the cycle) while the colour stays the same. If it never changes
    (e.g. a movement that is always green), returns the full cycle length.
    """
    now = approach_colour(phases[index][1], links)
    total = remaining_in_phase
    n = len(phases)
    for step in range(1, n + 1):
        dur, state = phases[(index + step) % n]
        if approach_colour(state, links) != now:
            return total
        total += dur
    return sum(d for d, _ in phases)


def choose_report_links(links: dict[int, tuple[str, str]], side: str) -> tuple[int, ...]:
    """Links of one approach to report: straight movement first, then right, then left."""
    for turn in ("S", "R", "L"):
        found = tuple(sorted(i for i, (s, t) in links.items() if s == side and t == turn))
        if found:
            return found
    return ()


def to_phase_state(
    approach: ApproachLinks,
    colour: str,
    seconds_remaining: float,
    now: datetime,
    *,
    confidence: float,
    timing: str,
    timing_label: str,
    geometry: str,
    geometry_label: str,
    sim_clock: str,
) -> dict:
    """One PhaseState JSON object (camelCase, matches packages/core PhaseState)."""
    return {
        "junctionId": approach.junction_id,
        "approachId": approach.approach_id,
        "colour": colour,
        "secondsRemaining": max(0, round(seconds_remaining)),
        "confidence": confidence,
        "source": "SIM",
        "updatedAt": now.isoformat(timespec="seconds"),
        "timing": timing,
        "timingLabel": timing_label,
        "geometry": geometry,
        "geometryLabel": geometry_label,
        "simClock": sim_clock,
    }
