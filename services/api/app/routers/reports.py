"""Citizen reports (from the app) and the monthly report data (printed to PDF in the dashboard)."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, insert, select, text, update

from .. import data_files as d
from ..auth import operator, viewer
from ..db import connect
from ..tables import citizen_reports
from .junctions import _metrics_rows, summarise

router = APIRouter(tags=["reports"])
ReportType = Literal["broken", "hidden", "timing_bad", "other"]


class NewReport(BaseModel):
    type: ReportType
    lat: float = Field(ge=26.7, le=27.1)
    lng: float = Field(ge=75.6, le=76.0)
    note: str | None = Field(None, max_length=500)
    junction_id: str | None = Field(None, pattern=r"^J0[1-8]$")


def nearest_junction(lat: float, lng: float) -> str | None:
    """Closest pilot junction within 300 m (PostGIS), used to group duplicate reports."""
    with connect() as c:
        row = c.execute(
            text(
                "SELECT id FROM junctions WHERE geom IS NOT NULL AND "
                "ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, 300) "
                "ORDER BY ST_Distance(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) LIMIT 1"
            ),
            {"lat": lat, "lng": lng},
        ).first()
    return row.id if row else None


@router.post("/reports", status_code=201)
def create_report(r: NewReport) -> dict:
    """Public: a citizen reports a broken / hidden / badly timed signal. No personal data stored."""
    jid = r.junction_id or nearest_junction(r.lat, r.lng)
    group = f"{jid or 'unmatched'}:{r.type}"  # duplicates = same junction + same problem type
    with connect() as c:
        rid = c.execute(
            insert(citizen_reports)
            .values(
                type=r.type,
                lat=round(r.lat, 4),
                lng=round(r.lng, 4),
                note=r.note,
                junction_id=jid,
                group_key=group,
            )
            .returning(citizen_reports.c.id)
        ).scalar_one()
        c.execute(
            text(
                "UPDATE citizen_reports SET geom = ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography "
                "WHERE id = :id"
            ),
            {"id": rid},
        )
    return {"id": rid, "junctionId": jid, "status": "New"}


@router.get("/reports")
def list_reports(_user: dict = Depends(viewer)) -> dict:
    with connect() as c:
        rows = [
            dict(x._mapping) for x in c.execute(select(citizen_reports).order_by(citizen_reports.c.id.desc()))
        ]
        groups = [
            dict(x._mapping)
            for x in c.execute(
                select(citizen_reports.c.group_key, func.count().label("count"))
                .group_by(citizen_reports.c.group_key)
                .order_by(func.count().desc())
            )
        ]
    return {"reports": rows, "groups": groups}


class StatusChange(BaseModel):
    status: Literal["New", "Assigned", "Fixed"]


@router.patch("/reports/{report_id}")
def set_status(report_id: int, s: StatusChange, _user: dict = Depends(operator)) -> dict:
    with connect() as c:
        n = c.execute(
            update(citizen_reports).where(citizen_reports.c.id == report_id).values(status=s.status)
        ).rowcount
    if not n:
        raise HTTPException(404, "Unknown report")
    return {"id": report_id, "status": s.status}


@router.get("/reports/monthly")
def monthly(month: str = Query("2026-05", pattern=r"^\d{4}-\d{2}$"), _user: dict = Depends(viewer)) -> dict:
    """Data for the monthly report (the dashboard prints it to PDF in English or Hindi)."""
    dates = [x for x in ("2026-05-11", "2026-05-12") if x.startswith(month)]
    per = {}
    for jid in [r["junction_id"] for r in d.registry()]:
        rows = [r for date in dates for r in _metrics_rows(jid, date, 0, 23)]
        per[jid] = summarise(rows) if rows else None
    with connect() as c:
        reports = c.execute(
            select(citizen_reports.c.status, func.count()).group_by(citizen_reports.c.status)
        ).all()
    return {
        "month": month,
        "surveyDates": dates,
        "junctions": per,
        "survey": d.survey_summary(),
        "citizenReports": {s: n for s, n in reports},
        "savings": None,  # before/after savings appear only after a pilot plan is applied and measured
        "note": "Baseline month: survey counts + assumed timing. Hours, fuel and CO2 saved need a measured after-period.",
        "sources": {"counts": "Survey, May 2026", "metrics": "SURVEY counts + ASSUMED timing"},
    }
