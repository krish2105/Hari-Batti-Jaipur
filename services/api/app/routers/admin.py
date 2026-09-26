"""Audit log (Admin) and read-only access to analysis results produced by the other services."""

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..audit_log import record
from ..auth import admin, viewer
from ..config import ROOT
from ..db import connect
from ..tables import audit_log

router = APIRouter(tags=["admin"])

# name -> result file written by services/sim or services/ml (only these can be read)
REPORTS = {
    "calibration": ROOT / "services/sim/reports/calibration_best.json",
    "calibration_trials": ROOT / "services/sim/reports/calibration_trials.csv",
    "controllers": ROOT / "services/ml/reports/controllers.json",
    "timespace": ROOT / "services/ml/reports/timespace.json",
    "forecast": ROOT / "services/ml/reports/forecast.json",
    "anomalies": ROOT / "services/ml/reports/anomalies.json",
    "cv": ROOT / "services/cv/reports/cv_eval.json",
}


class AuditEvent(BaseModel):
    action: Literal["export_pdf", "export_csv", "print_report"]
    detail: dict = Field(default_factory=dict)


@router.post("/audit/event", status_code=201)
def audit_event(ev: AuditEvent, user: dict = Depends(viewer)) -> dict:
    """The dashboard records exports here (PDF / CSV / printed reports)."""
    record(ev.action, user["email"], user["role"], ev.detail)
    return {"ok": True}


@router.get("/audit/log")
def audit_list(limit: int = Query(200, ge=1, le=1000), _user: dict = Depends(admin)) -> dict:
    with connect() as c:
        rows = [
            dict(r._mapping)
            for r in c.execute(select(audit_log).order_by(audit_log.c.id.desc()).limit(limit))
        ]
    return {"events": rows}


@router.get("/analytics/{name}")
def analytics(name: str) -> dict:
    """Results from calibration, controller comparison, forecasting, anomalies and computer vision.

    Returns {"available": false} until the producing workstream has written its file."""
    path = REPORTS.get(name)
    if path is None:
        raise HTTPException(404, f"Unknown result {name!r}; one of {sorted(REPORTS)}")
    if not path.exists():
        return {"name": name, "available": False}
    if path.suffix == ".csv":
        lines = path.read_text(encoding="utf-8").splitlines()
        head = lines[0].split(",") if lines else []
        return {"name": name, "available": True, "columns": head, "rows": [ln.split(",") for ln in lines[1:]]}
    return {"name": name, "available": True, **json.loads(path.read_text(encoding="utf-8"))}
