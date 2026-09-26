"""Pilot operations (P8 W13): tenants + onboarding, pilot KPI tracker, officer notes and pins,
"useful / not useful" feedback, weekly reviews, the police-entered timing-change log and the
Pilot Evidence Pack.

Everything here stores what people tell us or what was measured. Nothing is sent to a signal:
the timing-change log only RECORDS changes the police made in their own system.
"""

from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select, update

from .. import pilot as p
from ..audit_log import record
from ..auth import admin, operator, viewer
from ..connectors.source import load_config
from ..db import connect
from ..tables import (
    insight_feedback,
    officer_notes,
    pilot_kpis,
    pilots,
    tenant_members,
    tenant_sites,
    tenants,
    timing_changes,
    weekly_reviews,
)

router = APIRouter(tags=["pilot"])
Role = Literal["Viewer", "Operator", "Admin"]


# ---- helpers -------------------------------------------------------------------------------------


def _tenant(tenant_id: str, user: dict) -> dict:
    """The tenant if this user may see it (404 otherwise, so tenant names do not leak)."""
    if not p.can_see(user, tenant_id):
        raise HTTPException(404, "No such tenant")
    with connect() as c:
        return dict(c.execute(select(tenants).where(tenants.c.id == tenant_id)).one()._mapping)


def _pilot(pilot_id: int, user: dict) -> tuple[dict, dict]:
    with connect() as c:
        row = c.execute(select(pilots).where(pilots.c.id == pilot_id)).first()
    if row is None:
        raise HTTPException(404, "No such pilot")
    return dict(row._mapping), _tenant(row.tenant_id, user)


def _sites(tenant_id: str) -> list[dict]:
    with connect() as c:
        return [
            dict(r._mapping)
            for r in c.execute(
                select(tenant_sites)
                .where(tenant_sites.c.tenant_id == tenant_id)
                .order_by(tenant_sites.c.site_id)
            )
        ]


def _site_ids(tenant_id: str) -> set[str]:
    return {s["site_id"] for s in _sites(tenant_id)}


def _tenant_out(t: dict, with_sites: bool = False) -> dict:
    out = {"id": t["id"], "name": t["name"], "kind": t["kind"], "displayName": t["display_name"], "dataSources": t["data_sources"],
           "reportTemplate": {**p.DEFAULT_TEMPLATE, **(t["report_template"] or {})}, "openToAll": t["open_to_all"], "demo": t["demo"]}  # fmt: skip
    with connect() as c:
        out["pilots"] = [
            {"id": r.id, "name": r.name}
            for r in c.execute(select(pilots).where(pilots.c.tenant_id == t["id"]).order_by(pilots.c.id))
        ]
    if with_sites:
        out["sites"] = [
            {
                "id": s["site_id"],
                "name": s["name"],
                "kind": s["kind"],
                "lat": s["lat"],
                "lng": s["lng"],
                "source": s["source"],
            }
            for s in _sites(t["id"])
        ]
    return out


def _pilot_out(pl: dict, tenant_id: str) -> dict:
    return {"id": pl["id"], "tenantId": tenant_id, "name": pl["name"],
            "startDate": pl["start_date"].isoformat() if pl["start_date"] else None, "endDate": pl["end_date"].isoformat() if pl["end_date"] else None,
            "progress": p.pilot_day(pl["start_date"], pl["end_date"]), "kpis": p.kpi_rows(pl["id"], tenant_id)}  # fmt: skip


# ---- tenants and onboarding ----------------------------------------------------------------------


@router.get("/tenants")
def list_tenants(user: dict = Depends(viewer)) -> dict:
    return {"tenants": [_tenant_out(t) for t in p.visible_tenants(user)], "kinds": list(p.KINDS), "sources": list(p.SOURCES),
            "kpiTemplates": p.KPI_TEMPLATES, "reportSections": list(p.REPORT_SECTIONS),
            "connectors": [c["id"] for c in load_config()]}  # fmt: skip


@router.get("/tenants/{tenant_id}")
def get_tenant(tenant_id: str, user: dict = Depends(viewer)) -> dict:
    t = _tenant_out(_tenant(tenant_id, user), with_sites=True)
    if user["role"] == "Admin":
        with connect() as c:
            t["members"] = [
                {"email": r.email, "role": r.role}
                for r in c.execute(select(tenant_members).where(tenant_members.c.tenant_id == tenant_id))
            ]
    return t


class NewSite(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    id: str | None = Field(default=None, max_length=12)  # police tenants: J01-J08
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)


class NewMember(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=200)
    role: Role = "Viewer"


class Template(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    sections: list[str]
    footer: str = Field(default="", max_length=300)

    @field_validator("sections")
    @classmethod
    def _known(cls, v: list[str]) -> list[str]:
        bad = [s for s in v if s not in p.REPORT_SECTIONS]
        if bad or not v:
            raise ValueError(f"sections must be a non-empty subset of {', '.join(p.REPORT_SECTIONS)}")
        return v


class NewPilot(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    start: date | None = None
    end: date | None = None
    kpis: list[str] | None = None  # template keys to track (default: all for this kind)


class Onboarding(BaseModel):
    """Everything the onboarding wizard collects, submitted once at the end."""

    name: str = Field(min_length=2, max_length=80)
    kind: Literal["police", "campus", "township", "fleet", "other"]
    displayName: str | None = Field(default=None, max_length=120)
    sites: list[NewSite] = Field(min_length=1, max_length=60)
    dataSources: list[str] = Field(default_factory=list)
    members: list[NewMember] = Field(default_factory=list, max_length=100)
    pilot: NewPilot
    reportTemplate: Template | None = None


def _check_sources(values: list[str]) -> list[str]:
    known = {f"connector:{c['id']}" for c in load_config()}
    bad = [s for s in values if s not in p.SOURCES and s not in known]
    if bad:
        raise HTTPException(
            422, f"Unknown data sources: {', '.join(bad)} (use {', '.join(p.SOURCES)} or connector:<id>)"
        )
    return values


def _check_dates(start: date | None, end: date | None) -> None:
    if (start is None) != (end is None):
        raise HTTPException(422, "Give both a start and an end date, or neither")
    if start and end and not (1 <= (end - start).days + 1 <= 366):
        raise HTTPException(422, "The pilot must run 1–366 days, and end after it starts")


@router.post("/tenants", status_code=201)
def onboard(body: Onboarding, user: dict = Depends(admin)) -> dict:
    """Create a tenant with its sites, data sources, users, report template and first pilot."""
    tid = p.slugify(body.name)
    if not tid:
        raise HTTPException(422, "The organisation name needs letters or digits")
    if body.kind == "police":
        known = {r["junction_id"]: r["junction_name"] for r in p.d.registry()}
        ids = [s.id for s in body.sites]
        if any(i not in known for i in ids):
            raise HTTPException(
                422,
                "Police sites must be junctions from data/junction_registry.csv (J01–J08); none are invented",
            )
        sites = [
            {"site_id": i, "name": known[i], "kind": "junction", "lat": None, "lng": None, "source": "SURVEY"}
            for i in dict.fromkeys(ids)
        ]
    else:
        names = [s.name.strip() for s in body.sites]
        if len({n.lower() for n in names}) != len(names):
            raise HTTPException(422, "Site names must be different")
        src = "SIM" if body.dataSources == ["SIM"] else "FIELD"
        sites = [
            {
                "site_id": f"G{i}",
                "name": s.name.strip(),
                "kind": "gate",
                "lat": s.lat,
                "lng": s.lng,
                "source": src,
            }
            for i, s in enumerate(body.sites, start=1)
        ]
    _check_sources(body.dataSources)
    _check_dates(body.pilot.start, body.pilot.end)
    keys = body.pilot.kpis
    valid = {k["key"] for k in p.KPI_TEMPLATES[body.kind]}
    if keys is not None and (not keys or any(k not in valid for k in keys)):
        raise HTTPException(422, f"KPIs must be chosen from: {', '.join(sorted(valid))}")
    with connect() as c:
        if c.execute(select(tenants.c.id).where(tenants.c.id == tid)).first():
            raise HTTPException(409, f"A tenant called '{body.name}' already exists")
        p.create_tenant(c, {"id": tid, "name": body.name.strip(), "kind": body.kind, "display_name": body.displayName, "data_sources": body.dataSources,
                            "report_template": body.reportTemplate.model_dump() if body.reportTemplate else p.DEFAULT_TEMPLATE,
                            "demo": body.dataSources == ["SIM"]},
                        sites, [m.model_dump() for m in body.members], user["email"])  # fmt: skip
        pid = p.create_pilot(
            c, tid, body.kind, body.pilot.name, body.pilot.start, body.pilot.end, keys, user["email"]
        )
    record(
        "tenant_onboarded",
        user["email"],
        user["role"],
        {"tenant": tid, "sites": len(sites), "members": len(body.members)},
    )
    return {"id": tid, "pilotId": pid}


class TenantPatch(BaseModel):
    displayName: str | None = Field(default=None, max_length=120)
    reportTemplate: Template | None = None
    archived: bool | None = None  # true = offboard (hidden, records kept); there is no delete


@router.patch("/tenants/{tenant_id}")
def patch_tenant(tenant_id: str, body: TenantPatch, user: dict = Depends(admin)) -> dict:
    _tenant(tenant_id, user)
    values = {}
    if body.displayName is not None:
        values["display_name"] = body.displayName.strip() or None
    if body.reportTemplate is not None:
        values["report_template"] = body.reportTemplate.model_dump()
    if body.archived is not None:
        if tenant_id == p.JAIPUR:
            raise HTTPException(422, "The Jaipur police pilot tenant cannot be archived")
        values["archived"] = body.archived
    if values:
        with connect() as c:
            c.execute(update(tenants).where(tenants.c.id == tenant_id).values(**values))
    if body.archived:
        record("tenant_archived", user["email"], user["role"], {"tenant": tenant_id})
        return {"id": tenant_id, "archived": True}
    return _tenant_out(_tenant(tenant_id, user))


# ---- pilot and KPIs ------------------------------------------------------------------------------


@router.get("/pilots/{pilot_id}")
def get_pilot(pilot_id: int, user: dict = Depends(viewer)) -> dict:
    pl, t = _pilot(pilot_id, user)
    return _pilot_out(pl, t["id"])


class PilotPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    start: date | None = None
    end: date | None = None


@router.patch("/pilots/{pilot_id}")
def patch_pilot(pilot_id: int, body: PilotPatch, user: dict = Depends(admin)) -> dict:
    _, t = _pilot(pilot_id, user)
    _check_dates(body.start, body.end)
    values = {"start_date": body.start, "end_date": body.end}
    if body.name:
        values["name"] = body.name
    with connect() as c:
        c.execute(update(pilots).where(pilots.c.id == pilot_id).values(**values))
    record(
        "pilot_dates",
        user["email"],
        user["role"],
        {"pilot": pilot_id, "start": str(body.start), "end": str(body.end)},
    )
    pl, _ = _pilot(pilot_id, user)
    return _pilot_out(pl, t["id"])


class Measured(BaseModel):
    value: float | None = None
    source: Literal["SIM", "FIELD", "SURVEY", "CROWD", "ITMS"] | None = None
    note: str = Field(default="", max_length=300)


class KpiPatch(BaseModel):
    baseline: Measured | None = None
    current: Measured | None = None


@router.patch("/pilots/{pilot_id}/kpis/{kpi_id}")
def patch_kpi(pilot_id: int, kpi_id: int, body: KpiPatch, user: dict = Depends(operator)) -> dict:
    """Enter a measured baseline or current value. A value always needs its source."""
    _, t = _pilot(pilot_id, user)
    values: dict = {}
    for part, m in (("baseline", body.baseline), ("current", body.current)):
        if m is None:
            continue
        if m.value is not None and m.source is None:
            raise HTTPException(422, f"The {part} value needs a source (SIM, FIELD, SURVEY, CROWD or ITMS)")
        values |= {
            f"{part}_value": m.value,
            f"{part}_source": m.source if m.value is not None else None,
            f"{part}_note": m.note or None,
        }
    if not values:
        raise HTTPException(422, "Nothing to change")
    with connect() as c:
        n = c.execute(update(pilot_kpis).where(pilot_kpis.c.id == kpi_id, pilot_kpis.c.pilot_id == pilot_id)
                      .values(**values, updated_by=user["email"], updated_at=func.now())).rowcount  # fmt: skip
    if not n:
        raise HTTPException(404, "No such KPI in this pilot")
    record(
        "kpi_update",
        user["email"],
        user["role"],
        {"pilot": pilot_id, "kpi": kpi_id, "fields": sorted(values)},
    )
    return next(k for k in p.kpi_rows(pilot_id, t["id"]) if k["id"] == kpi_id)


# ---- officer notes and pins ----------------------------------------------------------------------


def _note_out(r) -> dict:
    return {"id": r.id, "siteId": r.site_id, "approach": r.approach, "text": r.text, "pinned": r.pinned, "resolved": r.resolved,
            "author": r.author, "createdAt": r.created_at.isoformat()}  # fmt: skip


@router.get("/tenants/{tenant_id}/notes")
def list_notes(
    tenant_id: str, site: str | None = Query(None, max_length=12), user: dict = Depends(viewer)
) -> dict:
    _tenant(tenant_id, user)
    q = select(officer_notes).where(officer_notes.c.tenant_id == tenant_id)
    if site:
        q = q.where(officer_notes.c.site_id == site)
    with connect() as c:
        rows = c.execute(q.order_by(officer_notes.c.pinned.desc(), officer_notes.c.created_at.desc())).all()
    return {"notes": [_note_out(r) for r in rows]}


class NewNote(BaseModel):
    siteId: str = Field(max_length=12)
    approach: str | None = Field(default=None, max_length=80)
    text: str = Field(min_length=1, max_length=1000)
    pinned: bool = False


@router.post("/tenants/{tenant_id}/notes", status_code=201)
def add_note(tenant_id: str, body: NewNote, user: dict = Depends(operator)) -> dict:
    _tenant(tenant_id, user)
    if body.siteId not in _site_ids(tenant_id):
        raise HTTPException(422, f"{body.siteId} is not a site of this tenant")
    with connect() as c:
        r = c.execute(officer_notes.insert().values(tenant_id=tenant_id, site_id=body.siteId, approach=body.approach, text=body.text.strip(),
                                                    pinned=body.pinned, author=user["email"]).returning(*officer_notes.c)).one()  # fmt: skip
    return _note_out(r)


class NotePatch(BaseModel):
    pinned: bool | None = None
    resolved: bool | None = None


@router.patch("/tenants/{tenant_id}/notes/{note_id}")
def patch_note(tenant_id: str, note_id: int, body: NotePatch, user: dict = Depends(operator)) -> dict:
    _tenant(tenant_id, user)
    values = {k: v for k, v in body.model_dump().items() if v is not None}
    if not values:
        raise HTTPException(422, "Nothing to change")
    with connect() as c:
        r = c.execute(update(officer_notes).where(officer_notes.c.id == note_id, officer_notes.c.tenant_id == tenant_id)
                      .values(**values).returning(*officer_notes.c)).first()  # fmt: skip
    if r is None:
        raise HTTPException(404, "No such note")
    return _note_out(r)


# ---- "useful / not useful" -----------------------------------------------------------------------


class Vote(BaseModel):
    insight: str = Field(pattern=r"^[A-Za-z0-9_.:-]{2,80}$")
    page: str | None = Field(default=None, max_length=80)
    useful: bool
    comment: str | None = Field(default=None, max_length=500)


@router.post("/tenants/{tenant_id}/feedback", status_code=201)
def vote(tenant_id: str, body: Vote, user: dict = Depends(viewer)) -> dict:
    """One vote per person per insight; voting again changes it."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    _tenant(tenant_id, user)
    stmt = pg_insert(insight_feedback).values(
        tenant_id=tenant_id,
        insight=body.insight,
        page=body.page,
        useful=body.useful,
        comment=body.comment,
        email=user["email"],
    )
    with connect() as c:
        c.execute(
            stmt.on_conflict_do_update(
                constraint="feedback_once",
                set_={
                    "useful": body.useful,
                    "comment": body.comment,
                    "page": body.page,
                    "created_at": func.now(),
                },
            )
        )
    return {"insight": body.insight, "useful": body.useful}


def feedback_summary(tenant_id: str, email: str | None = None) -> dict:
    with connect() as c:
        rows = c.execute(select(insight_feedback).where(insight_feedback.c.tenant_id == tenant_id)).all()
    items: dict[str, dict] = {}
    for r in rows:
        it = items.setdefault(
            r.insight, {"insight": r.insight, "page": r.page, "useful": 0, "notUseful": 0, "comments": []}
        )
        it["useful" if r.useful else "notUseful"] += 1
        if r.comment:
            it["comments"].append(r.comment)
    mine = {r.insight: r.useful for r in rows if email and r.email == email}
    return {"items": sorted(items.values(), key=lambda x: -(x["useful"] + x["notUseful"])), "mine": mine,
            "total": {"useful": sum(r.useful for r in rows), "notUseful": sum(not r.useful for r in rows)}}  # fmt: skip


@router.get("/tenants/{tenant_id}/feedback")
def get_feedback(tenant_id: str, user: dict = Depends(viewer)) -> dict:
    _tenant(tenant_id, user)
    return feedback_summary(tenant_id, user["email"])


# ---- weekly review -------------------------------------------------------------------------------


class Answers(BaseModel):
    """The five weekly questions."""

    daysUsed: int = Field(ge=0, le=7)  # 1. On how many days did you open the dashboard?
    mostUseful: str = Field(min_length=1, max_length=40)  # 2. Which screen helped most?
    actionTaken: bool  # 3. Did any insight lead to an action?
    actionNote: str = Field(default="", max_length=500)  #    ...which one?
    missing: str = Field(default="", max_length=1000)  # 4. What was wrong, missing or confusing?
    rating: int = Field(ge=1, le=5)  # 5. How useful was HariBatti this week (1-5)?


class Review(BaseModel):
    weekStart: date
    answers: Answers


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


@router.post("/pilots/{pilot_id}/reviews", status_code=201)
def add_review(pilot_id: int, body: Review, user: dict = Depends(operator)) -> dict:
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    _pilot(pilot_id, user)
    wk = _monday(body.weekStart)
    stmt = pg_insert(weekly_reviews).values(
        pilot_id=pilot_id, week_start=wk, answers=body.answers.model_dump(), email=user["email"]
    )
    with connect() as c:
        c.execute(
            stmt.on_conflict_do_update(
                constraint="review_once_a_week",
                set_={"answers": body.answers.model_dump(), "created_at": func.now()},
            )
        )
    return {"weekStart": wk.isoformat(), "answers": body.answers.model_dump()}


def reviews_of(pilot_id: int) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            select(weekly_reviews)
            .where(weekly_reviews.c.pilot_id == pilot_id)
            .order_by(weekly_reviews.c.week_start.desc())
        ).all()
    return [{"weekStart": r.week_start.isoformat(), "email": r.email, "answers": r.answers} for r in rows]


@router.get("/pilots/{pilot_id}/reviews")
def get_reviews(pilot_id: int, user: dict = Depends(viewer)) -> dict:
    _pilot(pilot_id, user)
    return {"reviews": reviews_of(pilot_id)}


# ---- timing-change log (entered by the police) ---------------------------------------------------


class Change(BaseModel):
    siteId: str = Field(max_length=12)
    changedOn: date
    timeWindow: str | None = Field(default=None, max_length=40)
    before: str = Field(min_length=1, max_length=300)
    after: str = Field(min_length=1, max_length=300)
    reason: str | None = Field(default=None, max_length=500)


def changes_of(tenant_id: str) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            select(timing_changes)
            .where(timing_changes.c.tenant_id == tenant_id)
            .order_by(timing_changes.c.changed_on.desc(), timing_changes.c.id.desc())
        ).all()
    return [{"id": r.id, "siteId": r.site_id, "changedOn": r.changed_on.isoformat(), "timeWindow": r.time_window, "before": r.before,
             "after": r.after, "reason": r.reason, "enteredBy": r.entered_by, "source": "FIELD"} for r in rows]  # fmt: skip


@router.get("/tenants/{tenant_id}/timing-changes")
def get_changes(tenant_id: str, user: dict = Depends(viewer)) -> dict:
    _tenant(tenant_id, user)
    return {
        "changes": changes_of(tenant_id),
        "note": "Entered by officers after they changed timings in their own system. HariBatti never changes a signal.",
    }


@router.post("/tenants/{tenant_id}/timing-changes", status_code=201)
def add_change(tenant_id: str, body: Change, user: dict = Depends(operator)) -> dict:
    _tenant(tenant_id, user)
    if body.siteId not in _site_ids(tenant_id):
        raise HTTPException(422, f"{body.siteId} is not a site of this tenant")
    if body.changedOn > p.today():
        raise HTTPException(422, "Record a change after it was made, not before")
    with connect() as c:
        c.execute(timing_changes.insert().values(tenant_id=tenant_id, site_id=body.siteId, changed_on=body.changedOn, time_window=body.timeWindow,
                                                 before=body.before, after=body.after, reason=body.reason, entered_by=user["email"]))  # fmt: skip
    record("timing_change_logged", user["email"], user["role"], {"tenant": tenant_id, "site": body.siteId})
    return changes_of(tenant_id)[0]


# ---- Pilot Evidence Pack -------------------------------------------------------------------------


@router.get("/pilots/{pilot_id}/evidence")
def evidence(pilot_id: int, user: dict = Depends(viewer)) -> dict:
    """Everything the printable Evidence Pack shows. Unmeasured KPIs are listed as placeholders."""
    pl, t = _pilot(pilot_id, user)
    out = _pilot_out(pl, t["id"])
    reviews = reviews_of(pilot_id)
    ans = [r["answers"] for r in reviews]
    with connect() as c:
        notes = [
            _note_out(r)
            for r in c.execute(
                select(officer_notes)
                .where(officer_notes.c.tenant_id == t["id"])
                .order_by(officer_notes.c.created_at.desc())
            )
        ]
    record("evidence_pack", user["email"], user["role"], {"pilot": pilot_id})
    return {
        "tenant": _tenant_out(t, with_sites=True),
        "pilot": out,
        "placeholders": [
            k["key"] for k in out["kpis"] if k["baseline"]["value"] is None or k["current"]["value"] is None
        ],
        "reviews": {
            "count": len(reviews),
            "avgRating": round(sum(a["rating"] for a in ans) / len(ans), 2) if ans else None,
            "avgDaysUsed": round(sum(a["daysUsed"] for a in ans) / len(ans), 1) if ans else None,
            "actions": [
                {"weekStart": r["weekStart"], "note": r["answers"].get("actionNote")}
                for r in reviews
                if r["answers"].get("actionTaken")
            ],
            "missing": [
                {"weekStart": r["weekStart"], "text": r["answers"]["missing"]}
                for r in reviews
                if r["answers"].get("missing")
            ],
            "weeks": reviews,
        },
        "feedback": feedback_summary(t["id"]),
        "changes": changes_of(t["id"]),
        "notes": notes,
        "sources": {
            "SURVEY": "Survey, May 2026 (professional turning-movement counts)",
            "ASSUMED": "Assumed signal timing until stopwatch data",
            "FIELD": "Measured or entered in the field by officers",
            "SIM": "Simulated",
            "ITMS": "Police signal feed (read-only)",
            "CROWD": "App users",
        },
        "readOnly": "HariBatti is read-only. It never changed any signal; officers made every change in their own system.",
    }
