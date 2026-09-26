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
    from ..audit_log import record

    record("plan_run", user["email"], user["role"], {"id": run_id, **req.model_dump(exclude_none=True)})
    threading.Thread(target=_job, args=(run_id, req), daemon=True).start()
    return {"id": run_id, "status": "queued"}


def _plan_summary(plan: dict) -> dict:
    """Cycle and the two main greens of one simulator plan (for the time-space diagram)."""
    phases = plan["phases"]
    greens = [p["duration_s"] for p in phases if p["kind"] == "green"]
    return {
        "cycleS": sum(p["duration_s"] for p in phases),
        "mainGreenS": greens[0] if greens else None,
        "crossGreenS": greens[1] if len(greens) > 1 else None,
        "phases": [{"kind": p["kind"], "durationS": p["duration_s"]} for p in phases],
        "offsetS": 0,  # every assumed plan runs with offset 0 (no coordination yet)
        "timing": plan.get("timing", "ASSUMED"),
    }


@router.get("/plans/library")
def plan_library() -> dict:
    """The signal plans the simulator uses, per junction (read from the sim build; SIM / ASSUMED)."""
    manifest = SIM_DIR / "build" / "schematic" / "manifest.json"
    if not manifest.exists():
        return {"available": False, "hint": "Run `make sim-build` first"}
    m = json.loads(manifest.read_text(encoding="utf-8"))
    plans = {
        pid: {
            "label": next(iter(per.values()))["label"] if per else pid,
            "junctions": {jid: _plan_summary(pl) for jid, pl in per.items()},
        }
        for pid, per in m["plans"].items()
    }
    return {
        "available": True,
        "geometryLabel": m["geometry_label"],
        "spacingM": 500,
        "spacingSource": "ASSUMED",
        "order": ["J08", "J07", "J06", "J05", "J04", "J03"],
        "plans": plans,
    }


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
