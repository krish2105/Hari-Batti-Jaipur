"""Data-subject rights (DPDP Act 2023; P8 W16): export the personal data we hold about you, and ask
for it to be erased or corrected. An Admin handles requests; erasure anonymises the person's email
everywhere it appears (notes, votes, reviews, change log, audit log) and disables the account.
Citizen app reports carry no personal data, so they are not part of this.
"""

import hashlib
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from ..audit_log import record
from ..auth import admin, viewer
from ..db import connect
from ..tables import (
    audit_log,
    insight_feedback,
    officer_notes,
    privacy_requests,
    tenant_members,
    timing_changes,
    users,
    weekly_reviews,
)

router = APIRouter(prefix="/privacy", tags=["privacy"])

# (table, email column) pairs that hold a person's email
PERSONAL = [(users, users.c.email), (audit_log, audit_log.c.email), (officer_notes, officer_notes.c.author),
            (insight_feedback, insight_feedback.c.email), (weekly_reviews, weekly_reviews.c.email),
            (timing_changes, timing_changes.c.entered_by), (tenant_members, tenant_members.c.email)]  # fmt: skip


def _plain(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


@router.get("/me/export")
def export_mine(user: dict = Depends(viewer)) -> dict:
    """Everything stored under your email, as JSON (DPDP right to access)."""
    out = {}
    with connect() as c:
        for table, col in PERSONAL:
            out[table.name] = [
                {k: _plain(v) for k, v in r._mapping.items()}
                for r in c.execute(select(table).where(col == user["email"]))
            ]
    record("privacy_export", user["email"], user["role"])
    return {"email": user["email"], "exportedAt": datetime.now(UTC).isoformat(), "data": out,
            "notStored": "Sign-in codes are stored only as hashes and expire in 10 minutes; citizen reports hold no personal data."}  # fmt: skip


class NewRequest(BaseModel):
    kind: Literal["erase", "correct"]
    note: str | None = Field(default=None, max_length=1000)


@router.post("/requests", status_code=201)
def new_request(body: NewRequest, user: dict = Depends(viewer)) -> dict:
    with connect() as c:
        rid = c.execute(
            privacy_requests.insert()
            .values(email=user["email"], kind=body.kind, note=body.note)
            .returning(privacy_requests.c.id)
        ).scalar_one()
    record("privacy_request", user["email"], user["role"], {"kind": body.kind, "id": rid})
    return {"id": rid, "status": "open", "note": "An Admin will handle this within 30 days."}


@router.get("/requests")
def list_requests(_user: dict = Depends(admin)) -> dict:
    with connect() as c:
        rows = c.execute(select(privacy_requests).order_by(privacy_requests.c.created_at.desc())).all()
    return {"requests": [{k: _plain(v) for k, v in r._mapping.items()} for r in rows]}


class Handle(BaseModel):
    status: Literal["done", "rejected"]


def pseudonym(email: str) -> str:
    return "erased-" + hashlib.sha256(email.encode()).hexdigest()[:10]


@router.patch("/requests/{request_id}")
def handle(request_id: int, body: Handle, user: dict = Depends(admin)) -> dict:
    """Close a request. Closing an erase request as done anonymises the person's email everywhere."""
    with connect() as c:
        req = c.execute(select(privacy_requests).where(privacy_requests.c.id == request_id)).first()
        if req is None:
            raise HTTPException(404, "No such request")
        if req.status != "open":
            raise HTTPException(409, "This request is already closed")
        changed = 0
        if body.status == "done" and req.kind == "erase":
            alias = pseudonym(req.email)
            for table, col in PERSONAL:
                values = {col.name: alias}
                if table is users:
                    values["role"] = "Viewer"  # the account can no longer sign in with the old email
                changed += c.execute(update(table).where(col == req.email).values(**values)).rowcount
            c.execute(update(privacy_requests).where(privacy_requests.c.id == request_id).values(email=alias))
        c.execute(
            update(privacy_requests)
            .where(privacy_requests.c.id == request_id)
            .values(status=body.status, handled_by=user["email"], handled_at=datetime.now(UTC))
        )
    record(
        "privacy_request_closed",
        user["email"],
        user["role"],
        {"id": request_id, "status": body.status, "rowsAnonymised": changed},
    )
    return {"id": request_id, "status": body.status, "rowsAnonymised": changed}
