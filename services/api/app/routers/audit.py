"""Fairness audit: every junction approach ranked by green starvation and pedestrian time."""

from fastapi import APIRouter, Query
from sqlalchemy import select

from ..db import connect
from ..tables import metrics_hourly

router = APIRouter(tags=["audit"])


@router.get("/audit/fairness")
def fairness(date: str = Query("2026-05-11"), limit: int = Query(10, ge=1, le=64)) -> dict:
    """Worst approach-hours first (lowest green starvation ratio), from the hourly metrics detail."""
    with connect() as c:
        rows = c.execute(select(metrics_hourly).where(metrics_hourly.c.survey_date == date)).all()
    items = []
    for r in rows:
        for ap in (r.detail or {}).get("approaches", []):
            items.append(
                {
                    "junctionId": r.junction_id,
                    "hour": r.hour,
                    "hourStart": f"{r.hour:02d}:00",  # metrics_hourly.hour is the clock hour
                    "approach": ap["approach"],
                    "starvation": ap["starvation"],
                    "redWaitS": ap["red_wait_s"],
                    "pedRatio": ap.get("ped_ratio"),
                    "vc": ap.get("vc"),
                    "flowPcuH": ap.get("flow_pcu_h"),
                    "greenS": ((r.detail or {}).get("green_s") or {}).get(ap["approach"]),
                    "cycleS": (r.detail or {}).get("cycle_s"),
                }
            )
    worst: dict[tuple[str, str], dict] = {}
    for it in items:
        k = (it["junctionId"], it["approach"])
        if k not in worst or it["starvation"] < worst[k]["starvation"]:
            worst[k] = it
    ranked = sorted(worst.values(), key=lambda x: (x["starvation"], -(x["redWaitS"] or 0)))
    return {
        "date": date,
        "top": ranked[:limit],
        "count": len(ranked),
        "method": "Starvation = green given ÷ green needed at x = 0.9; ped ratio uses ASSUMED crossing widths",
        "source": "SURVEY counts + ASSUMED timing",
    }
