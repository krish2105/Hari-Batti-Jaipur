"""Commercial surfaces (P8 W17): pilot / contact requests from the website, and usage metering per
tenant with a CSV export for invoice support. No payment processing.

The public form is protected without third-party services: a hidden honeypot field, a minimum fill
time, a per-IP rate limit and strict field validation.
"""

import csv
import io
import time
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update

from .. import metering, monitor
from ..auth import admin
from ..db import connect
from ..ratelimit import per_ip
from ..tables import leads, tenant_members, tenant_sites, tenants, usage_daily

router = APIRouter(tags=["commercial"])
Offer = Literal["pilot", "audit", "signal_command", "citizen_data", "fleet_api", "other"]


class Lead(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    organisation: str = Field(min_length=2, max_length=150)
    role: str | None = Field(default=None, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=200)
    phone: str | None = Field(default=None, pattern=r"^[0-9+ ()-]{7,20}$")
    offer: Offer = "pilot"
    city: str | None = Field(default=None, max_length=80)
    message: str | None = Field(default=None, max_length=2000)
    consent: Literal[True]  # the person agreed that we may contact them about this request
    website: str = Field(default="", max_length=0)  # honeypot: people never see or fill it
    startedAt: float = Field(description="ms since epoch when the form was shown")


@router.post("/leads", status_code=201)
def new_lead(body: Lead, request: Request) -> dict:
    per_ip(request, "lead", limit=5, window_s=3600)
    if time.time() * 1000 - body.startedAt < 3000:  # filled in under 3 s: a bot
        raise HTTPException(422, "Please take a moment to fill in the form")
    with connect() as c:
        lid = c.execute(
            leads.insert()
            .values(**body.model_dump(exclude={"consent", "website", "startedAt"}))
            .returning(leads.c.id)
        ).scalar_one()
    monitor.notify(
        monitor.Event(
            f"lead:{lid}",
            "lead",
            True,
            f"New {body.offer} request from {body.organisation} ({body.city or '—'})",
        )
    )
    return {"id": lid, "received": True}


@router.get("/leads")
def list_leads(_user: dict = Depends(admin)) -> dict:
    with connect() as c:
        rows = c.execute(select(leads).order_by(leads.c.created_at.desc()).limit(500)).all()
    return {
        "leads": [
            {
                **{k: v for k, v in r._mapping.items() if k != "created_at"},
                "createdAt": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }


class LeadPatch(BaseModel):
    status: Literal["new", "contacted", "closed"]


@router.patch("/leads/{lead_id}")
def patch_lead(lead_id: int, body: LeadPatch, _user: dict = Depends(admin)) -> dict:
    with connect() as c:
        n = c.execute(update(leads).where(leads.c.id == lead_id).values(status=body.status)).rowcount
    if not n:
        raise HTTPException(404, "No such request")
    return {"id": lead_id, "status": body.status}


def usage(month: str) -> list[dict]:
    """Per tenant for one month: sites, members, active users, API calls."""
    y, m = map(int, month.split("-"))
    start, end = date(y, m, 1), date(y + (m == 12), m % 12 + 1, 1)
    metering.flush()
    with connect() as c:
        ts = c.execute(
            select(tenants).where(tenants.c.archived.is_(False)).order_by(tenants.c.created_at)
        ).all()
        sites = dict(
            c.execute(select(tenant_sites.c.tenant_id, func.count()).group_by(tenant_sites.c.tenant_id)).all()
        )
        members = dict(
            c.execute(
                select(tenant_members.c.tenant_id, func.count()).group_by(tenant_members.c.tenant_id)
            ).all()
        )
        calls = {r.tenant_id: (r.calls, r.users) for r in c.execute(
            select(usage_daily.c.tenant_id, func.sum(usage_daily.c.calls).label("calls"), func.count(func.distinct(usage_daily.c.email)).label("users"))
            .where(usage_daily.c.day >= start, usage_daily.c.day < end).group_by(usage_daily.c.tenant_id))}  # fmt: skip
    return [{"tenantId": t.id, "tenant": t.name, "kind": t.kind, "demo": t.demo, "month": month, "sitesActive": sites.get(t.id, 0),
             "members": members.get(t.id, 0), "activeUsers": calls.get(t.id, (0, 0))[1], "apiCalls": int(calls.get(t.id, (0, 0))[0] or 0)} for t in ts]  # fmt: skip


@router.get("/metering")
def get_metering(
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), _user: dict = Depends(admin)
) -> dict:
    return {
        "month": month,
        "tenants": usage(month),
        "note": "Invoice support only: no payment is taken in HariBatti.",
    }


@router.get("/metering.csv")
def metering_csv(
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), _user: dict = Depends(admin)
) -> Response:
    rows = usage(month)
    buf = io.StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=[
            "month",
            "tenantId",
            "tenant",
            "kind",
            "demo",
            "sitesActive",
            "members",
            "activeUsers",
            "apiCalls",
        ],
    )
    w.writeheader()
    w.writerows(rows)
    return Response(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="haribatti-usage-{month}.csv"'},
    )
