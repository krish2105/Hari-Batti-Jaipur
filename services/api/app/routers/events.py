"""Event mode templates and green-corridor planning (recommendations only — never applied)."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .. import data_files as d

router = APIRouter(tags=["events"])

EVENTS = [
    {
        "id": "sms-match",
        "name": "SMS Stadium cricket match",
        "nameHi": "एसएमएस स्टेडियम क्रिकेट मैच",
        "window": "16:00–23:30",
        "focus": ["J03", "J04"],
        "advice": "Longer main-road green towards Sanganer Stadium after the match; push diversion to the app.",
    },
    {
        "id": "teej",
        "name": "Teej procession",
        "nameHi": "तीज की सवारी",
        "window": "17:00–21:00",
        "focus": ["J05", "J06"],
        "advice": "Flashing amber on closed arms; diversion via cross roads.",
    },
    {
        "id": "gangaur",
        "name": "Gangaur procession",
        "nameHi": "गणगौर की सवारी",
        "window": "17:00–21:00",
        "focus": ["J06", "J07"],
        "advice": "Hold cross-road greens shorter; alert riders in the app.",
    },
    {
        "id": "vip",
        "name": "VIP movement",
        "nameHi": "वीआईपी मूवमेंट",
        "window": "as notified",
        "focus": ["J03", "J08"],
        "advice": "Green corridor on request of the traffic control room only.",
    },
]


@router.get("/events")
def events() -> dict:
    return {
        "events": EVENTS,
        "note": "Templates for discussion, not police plans. Nothing is applied to signals.",
    }


class Corridor(BaseModel):
    junctions: list[str] = Field(min_length=1, max_length=8)
    speed_kmh: float = Field(30, ge=10, le=60)
    spacing_m: float = Field(500, ge=100, le=3000)


@router.post("/events/green-corridor")
def green_corridor(c: Corridor) -> dict:
    """Ambulance green corridor: when each junction would need a green hold (recommendation only)."""
    known = {r["junction_id"] for r in d.registry()}
    order = [j for j in c.junctions if j in known]
    step = c.spacing_m / (c.speed_kmh / 3.6)
    return {
        "holds": [{"junctionId": j, "arriveAfterS": round(i * step)} for i, j in enumerate(order)],
        "assumptions": {"speedKmh": c.speed_kmh, "spacingM": c.spacing_m, "spacingSource": "ASSUMED"},
        "note": "Recommendation for the control room. HariBatti never holds a real signal.",
    }
