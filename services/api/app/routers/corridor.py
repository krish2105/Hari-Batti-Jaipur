"""Corridor KPIs for the Mansarovar pilot."""

from fastapi import APIRouter, Query

from .. import data_files as d
from ..db import db_available
from .junctions import _metrics_rows, summarise

router = APIRouter(tags=["corridor"])


@router.get("/corridor/mansarovar/kpis")
def corridor_kpis(
    date: str = Query("2026-05-11"),
    frm: int = Query(0, alias="from", ge=0, le=23),
    to: int = Query(23, ge=0, le=23),
) -> dict:
    survey = [s for rows in d.survey_summary().values() for s in rows if s["surveyDate"] == date]
    out = {
        "corridor": "Mansarovar (Mansarovar Metro ↔ Sanganer Stadium)",
        "date": date,
        "junctionsSurveyed": len(survey),
        "totalVehicles24h": sum(s["totalVeh"] for s in survey),
        "busiestPmPeak": max(
            (
                {"junctionId": j, **x}
                for j, rows in d.survey_summary().items()
                for x in rows
                if x["surveyDate"] == date
            ),
            key=lambda x: x["pmPeakPcuHr"],
            default=None,
        ),
        "twoWheelerShareAvg": round(sum(s["twoWheelerPct"] for s in survey) / len(survey), 1)
        if survey
        else None,
        "surveySource": "Survey, May 2026",
    }
    if db_available():
        per = {}
        for jid in [r["junction_id"] for r in d.registry()]:
            rows = _metrics_rows(jid, date, frm, to)
            if rows:
                per[jid] = summarise(rows)
        if per:
            out["health"] = {j: v["health"] for j, v in per.items()}
            out["healthAvg"] = round(sum(v["health"] for v in per.values()) / len(per), 1)
            out["worstJunction"] = min(per, key=lambda j: per[j]["health"])
            out["metricsSource"] = "SURVEY counts + ASSUMED timing"
    return out
