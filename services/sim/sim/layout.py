"""Work out where each approach sits (west/north/east/south) from the survey's own turn labels.

India drives on the left. Standing on an approach and facing the junction, "L" goes to the arm
on your left, "S" straight across, "R" to your right. So the 12 surveyed movements fix the
arm order around every junction; we only have to pick which arm is "west".

The corridor road runs west -> east:
  J03-J08: "Mansarover Metro" (west) -> "Sanganer Stadium" (east)
  J01-J02: "B2BYPASS" (west) -> "SUMER NAGAR" (east)   [B2 Bypass side, schematic]
"""

from dataclasses import dataclass

from .demand import Movement

SIDES = ("W", "N", "E", "S")  # clockwise when seen from above
# Coming FROM side X (heading into the junction), which side does each turn reach?
TURN_TARGET = {
    "W": {"L": "N", "S": "E", "R": "S"},
    "N": {"L": "E", "S": "S", "R": "W"},
    "E": {"L": "S", "S": "W", "R": "N"},
    "S": {"L": "W", "S": "N", "R": "E"},
}
WEST_ARM = {"J01": "B2BYPASS", "J02": "B2BYPASS"}  # others: "Mansarover Metro"
DEFAULT_WEST_ARM = "Mansarover Metro"
MAIN_ROAD_SIDES = ("W", "E")


@dataclass(frozen=True)
class JunctionLayout:
    junction_id: str
    side_of: dict[str, str]  # approach name -> side
    inconsistencies: tuple[str, ...]  # survey turn labels that disagree with the derived layout

    @property
    def approach_at(self) -> dict[str, str]:
        return {side: name for name, side in self.side_of.items()}

    def is_main(self, approach: str) -> bool:
        return self.side_of[approach] in MAIN_ROAD_SIDES


def derive_layout(junction_id: str, movements: list[Movement]) -> JunctionLayout:
    """Place the four arms using the west arm's L/S/R targets, then check the other 9 movements."""
    west = WEST_ARM.get(junction_id, DEFAULT_WEST_ARM)
    mine = [m for m in movements if m.junction_id == junction_id]
    side_of = {west: "W"}
    for m in mine:
        if m.from_approach == west:
            side_of[m.to_approach] = TURN_TARGET["W"][m.turn]
    if len(side_of) != 4:
        raise ValueError(f"{junction_id}: could not place all 4 arms from {west!r}: {side_of}")
    problems = tuple(
        f"{m.from_approach} -{m.turn}-> {m.to_approach}"
        for m in mine
        if TURN_TARGET[side_of[m.from_approach]][m.turn] != side_of[m.to_approach]
    )
    return JunctionLayout(junction_id, side_of, problems)
