"""Field study (P8 W14): invite-only enrolment, server-randomised runs and trimmed trace upload.

Participants never sign in: enrolling with an invite code returns a study token that only works on
/study/* routes. Admins create invites and export the anonymous data for services/ml/study/analyse.py.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from .. import study
from ..audit_log import record
from ..auth import admin
from ..config import settings
from ..db import connect
from ..ratelimit import per_ip
from ..tables import study_invites, study_participants, study_runs, study_traces

router = APIRouter(prefix="/study", tags=["study"])
STUDY_TTL = timedelta(days=60)


def _hash(code: str) -> str:
    return hashlib.sha256(f"study:{code.strip().upper()}".encode()).hexdigest()


def make_study_token(pid: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"study": pid, "iat": now, "exp": now + STUDY_TTL}, settings().jwt_secret, algorithm="HS256"
    )


def participant(request: Request) -> str:
    """The enrolled participant behind a study token (never an officer session)."""
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("bearer "):
        raise HTTPException(401, "Study token required")
    try:
        pid = jwt.decode(h[7:], settings().jwt_secret, algorithms=["HS256"]).get("study")
    except jwt.PyJWTError as e:
        raise HTTPException(401, "Study token expired") from e
    if not pid:
        raise HTTPException(401, "Study token required")
    with connect() as c:
        row = c.execute(select(study_participants.c.withdrawn).where(study_participants.c.id == pid)).first()
    if row is None or row.withdrawn:
        raise HTTPException(403, "Not enrolled in the study")
    return pid


participant.required_role = "StudyParticipant"  # read by the access-matrix test


class NewInvite(BaseModel):
    label: str = Field(min_length=2, max_length=80)
    maxParticipants: int = Field(default=30, ge=1, le=200)


@router.post("/invites", status_code=201)
def new_invite(body: NewInvite, user: dict = Depends(admin)) -> dict:
    """Create an invite code. It is shown once; only its hash is stored."""
    code = study.new_invite_code()
    with connect() as c:
        c.execute(
            study_invites.insert().values(
                code_hash=_hash(code),
                label=body.label,
                max_participants=body.maxParticipants,
                created_by=user["email"],
            )
        )
    record("study_invite", user["email"], user["role"], {"label": body.label})
    return {"code": code, "label": body.label, "maxParticipants": body.maxParticipants}


class Enrol(BaseModel):
    code: str = Field(min_length=6, max_length=12)
    vehicle: Literal["car", "scooter", "motorbike", "auto"]
    consent: Literal[True]


@router.post("/enrol", status_code=201)
def enrol(body: Enrol, request: Request) -> dict:
    per_ip(request, "study-enrol", limit=10, window_s=3600)
    h = _hash(body.code)
    with connect() as c:
        inv = c.execute(select(study_invites).where(study_invites.c.code_hash == h)).first()
        if inv is None or not inv.active or inv.used >= inv.max_participants:
            raise HTTPException(403, "This invite code is not valid")
        pid = study.new_participant_id()
        c.execute(study_participants.insert().values(id=pid, vehicle=body.vehicle, invite_hash=h))
        c.execute(
            update(study_invites).where(study_invites.c.code_hash == h).values(used=study_invites.c.used + 1)
        )
    return {"participantId": pid, "token": make_study_token(pid)}


@router.post("/runs", status_code=201)
def start_run(pid: str = Depends(participant)) -> dict:
    """Start a run; the server assigns advice ON or OFF (permuted blocks of two)."""
    with connect() as c:
        prev = [
            r.arm
            for r in c.execute(
                select(study_runs.c.arm).where(study_runs.c.participant_id == pid).order_by(study_runs.c.id)
            )
        ]
        arm = study.next_arm(prev)
        rid = c.execute(
            study_runs.insert().values(participant_id=pid, arm=arm).returning(study_runs.c.id)
        ).scalar_one()
    return {"runId": rid, "arm": arm, "runNumber": len(prev) + 1}


class Trace(BaseModel):
    points: list[list[float]] = Field(description="[t_s, lat, lng, speed_kmh] at about 1 Hz")
    direction: Literal["east", "west"]


@router.post("/runs/{run_id}/trace", status_code=201)
def upload(run_id: int, body: Trace, pid: str = Depends(participant)) -> dict:
    if reason := study.validate(body.points):
        raise HTTPException(422, reason)
    kept = study.trim(body.points)
    if not kept:
        raise HTTPException(422, "The run is too short: nothing is left after removing 200 m at each end")
    with connect() as c:
        run = c.execute(
            select(study_runs).where(study_runs.c.id == run_id, study_runs.c.participant_id == pid)
        ).first()
        if run is None:
            raise HTTPException(404, "No such run")
        if run.status != "started":
            raise HTTPException(409, "This run was already uploaded")
        c.execute(study_traces.insert().values(run_id=run_id, points=kept))
        c.execute(update(study_runs).where(study_runs.c.id == run_id).values(
            status="uploaded", direction=body.direction, points_kept=len(kept), points_trimmed=len(body.points) - len(kept), uploaded_at=datetime.now(UTC)))  # fmt: skip
    return {"runId": run_id, "pointsKept": len(kept), "pointsTrimmed": len(body.points) - len(kept)}


@router.post("/withdraw")
def withdraw(pid: str = Depends(participant)) -> dict:
    """A participant leaves the study: their traces are deleted at once (runs are kept as counts only)."""
    with connect() as c:
        runs = [r.id for r in c.execute(select(study_runs.c.id).where(study_runs.c.participant_id == pid))]
        if runs:
            c.execute(study_traces.delete().where(study_traces.c.run_id.in_(runs)))
        c.execute(update(study_participants).where(study_participants.c.id == pid).values(withdrawn=True))
    return {"withdrawn": True, "tracesDeleted": len(runs)}


@router.get("/summary")
def summary(_user: dict = Depends(admin)) -> dict:
    with connect() as c:
        runs = c.execute(select(study_runs)).all()
        people = c.execute(select(study_participants)).all()
    by_arm = {a: sum(1 for r in runs if r.arm == a and r.status == "uploaded") for a in ("advice", "control")}
    return {
        "participants": len(people),
        "withdrawn": sum(p.withdrawn for p in people),
        "runsUploaded": by_arm,
        "runsStarted": len(runs),
        "target": 20,
    }


@router.get("/export")
def export(_user: dict = Depends(admin)) -> dict:
    """Anonymous runs with trimmed traces, for services/ml/study/analyse.py (source FIELD)."""
    with connect() as c:
        rows = c.execute(select(study_runs, study_traces.c.points, study_participants.c.vehicle)
                         .join(study_traces, study_traces.c.run_id == study_runs.c.id)
                         .join(study_participants, study_participants.c.id == study_runs.c.participant_id)).all()  # fmt: skip
    return {
        "source": "FIELD",
        "runs": [
            {
                "runId": r.id,
                "participant": r.participant_id,
                "vehicle": r.vehicle,
                "arm": r.arm,
                "direction": r.direction,
                "points": r.points,
            }
            for r in rows
        ],
    }
