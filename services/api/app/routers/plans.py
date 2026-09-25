"""Plan Studio: run the SUMO what-if (services/sim `simulate`) as a background job."""

import json
import logging
import subprocess
import threading
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import insert, select, update

from ..auth import operator
from ..config import ROOT
from ..db import connect
from ..tables import plan_runs

router = APIRouter(tags=["plans"])
log = logging.getLogger("haribatti.plans")
SIM_DIR = ROOT / "services" / "sim"
PlanId = Literal["demand2", "webster4", "even"]


class CustomPlan(BaseModel):
    cycle_s: int = Field(ge=40, le=240)
    main_green_s: int = Field(ge=10, le=200)
    cross_green_s: int = Field(ge=10, le=200)


class SimulateRequest(BaseModel):
    baseline: PlanId = "even"
    proposed: PlanId | None = "demand2"
    junction_id: str | None = Field(None, pattern=r"^J0[1-8]$")
    custom: CustomPlan | None = None
    start: str = Field("18:15", pattern=r"^\d{2}:\d{2}$")
    minutes: int = Field(15, ge=5, le=60)


def _job(run_id: str, req: SimulateRequest) -> None:
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "sim",
        "simulate",
        "--baseline",
        req.baseline,
        "--start",
        req.start,
        "--minutes",
        str(req.minutes),
    ]
    if req.custom:
        cmd += ["--junction", req.junction_id or "", "--custom", req.custom.model_dump_json()]
    elif req.proposed:
        cmd += ["--proposed", req.proposed]
    with connect() as c:
        c.execute(update(plan_runs).where(plan_runs.c.id == run_id).values(status="running"))
    try:
        res = subprocess.run(cmd, cwd=SIM_DIR, capture_output=True, text=True, timeout=1800, check=True)
        result = json.loads(res.stdout.strip().splitlines()[-1])
        values = {"status": "done", "result": result}
    except (subprocess.SubprocessError, ValueError, IndexError) as e:
        err = getattr(e, "stderr", None) or str(e)
        log.warning("plan run %s failed: %s", run_id, err[-500:])
        values = {"status": "failed", "error": err[-1000:]}
    with connect() as c:
        c.execute(update(plan_runs).where(plan_runs.c.id == run_id).values(**values))


@router.post("/plans/simulate", status_code=202)
def start_simulation(req: SimulateRequest, user: dict = Depends(operator)) -> dict:
    """Queue a before/after simulation. Poll GET /plans/simulate/{id}. SIM results only."""
    if req.custom and not req.junction_id:
        raise HTTPException(422, "A custom plan needs junction_id")
    run_id = uuid.uuid4().hex[:12]
    with connect() as c:
        c.execute(
            insert(plan_runs).values(
                id=run_id, status="queued", request={**req.model_dump(), "by": user["email"]}
            )
        )
    threading.Thread(target=_job, args=(run_id, req), daemon=True).start()
    return {"id": run_id, "status": "queued"}


@router.get("/plans/simulate/{run_id}")
def simulation_status(run_id: str) -> dict:
    with connect() as c:
        row = c.execute(select(plan_runs).where(plan_runs.c.id == run_id)).first()
    if row is None:
        raise HTTPException(404, "Unknown run")
    return {
        "id": row.id,
        "status": row.status,
        "request": row.request,
        "result": row.result,
        "error": row.error,
    }
