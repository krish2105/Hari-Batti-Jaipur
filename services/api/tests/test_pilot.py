"""Pilot operations (P8 W13): tenants and onboarding, KPI tracker, notes, feedback, weekly reviews,
timing-change log, evidence pack and access rules. Tests create their own "test-…" tenants and
remove them afterwards, so the real Jaipur pilot records are never touched."""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import delete

from app.auth import make_token
from app.pilot import pilot_day, today
from tests.conftest import needs_db


def H(email: str, role: str) -> dict:
    return {"Authorization": f"Bearer {make_token(email, role)}"}


ADMIN = H("admin@test.local", "Admin")
OPER = H("operator@test.local", "Operator")
VIEW = H("viewer@test.local", "Viewer")


def test_pilot_day_states():
    s, e = date(2026, 10, 1), date(2026, 11, 29)
    assert pilot_day(None, None)["status"] == "not_started"
    assert pilot_day(s, e, date(2026, 9, 30)) == {"status": "scheduled", "day": 0, "days": 60}
    assert pilot_day(s, e, date(2026, 10, 1)) == {"status": "running", "day": 1, "days": 60}
    assert pilot_day(s, e, date(2026, 12, 1))["status"] == "ended"


@pytest.fixture
def made():
    """Tenant ids created by a test; deleted (with everything under them) afterwards."""
    ids: list[str] = []
    yield ids
    from app.db import connect
    from app.tables import tenants

    with connect() as c:
        for t in ids:
            assert t.startswith("test-")
            c.execute(delete(tenants).where(tenants.c.id == t))


def onboard(client, made, kind="police", **kw) -> dict:
    name = f"Test {kind} {uuid.uuid4().hex[:8]}"
    sites = (
        [{"id": "J05", "name": "x"}, {"id": "J06", "name": "x"}]
        if kind == "police"
        else [{"name": "Main Gate"}, {"name": "North Gate"}, {"name": "Hostel Gate"}]
    )
    body = {"name": name, "kind": kind, "sites": sites, "dataSources": ["SIM"] if kind != "police" else ["SURVEY"],
            "members": [{"email": "operator@test.local", "role": "Operator"}, {"email": "member@test.local", "role": "Viewer"}],
            "pilot": {"name": "Pilot", "start": "2026-09-01", "end": "2026-10-30"},
            "reportTemplate": {"title": "Evidence", "sections": ["kpis", "notes", "sources"], "footer": "f"}, **kw}  # fmt: skip
    r = client.post("/tenants", headers=ADMIN, json=body)
    assert r.status_code == 201, r.text
    made.append(r.json()["id"])
    return r.json()


@needs_db
def test_seeded_tenants_and_measured_baselines(client):
    ts = {t["id"]: t for t in client.get("/tenants", headers=OPER).json()["tenants"]}
    assert {"jaipur-police", "campus-demo-sim"} <= set(ts)
    assert ts["campus-demo-sim"]["demo"] is True
    pilot = client.get(f"/pilots/{ts['jaipur-police']['pilots'][0]['id']}", headers=OPER).json()
    kpis = {k["key"]: k for k in pilot["kpis"]}
    assert list(kpis) == ["vc_over_09", "red_wait_s", "stops_per_trip", "ped_clearance_pct", "timer_error_s"]
    assert (
        kpis["stops_per_trip"]["baseline"]["value"] is None
    )  # needs GPS drives: a placeholder, never a guess
    if kpis["vc_over_09"]["baseline"]["value"] is not None:  # metrics computed (make api / CI)
        assert (
            kpis["vc_over_09"]["baseline"]["source"] == "SURVEY counts + ASSUMED timing"
            and kpis["vc_over_09"]["baseline"]["auto"]
        )


@needs_db
def test_onboarding_and_tenant_isolation(client, made):
    t = onboard(client, made, kind="campus")
    got = client.get(f"/tenants/{t['id']}", headers=ADMIN).json()
    assert [s["id"] for s in got["sites"]] == ["G1", "G2", "G3"] and {s["source"] for s in got["sites"]} == {
        "SIM"
    }
    assert sorted(m["email"] for m in got["members"]) == ["member@test.local", "operator@test.local"]
    assert got["reportTemplate"]["title"] == "Evidence"
    assert client.get(f"/tenants/{t['id']}", headers=H("member@test.local", "Operator")).status_code == 200
    assert client.get(f"/tenants/{t['id']}", headers=VIEW).status_code == 404  # not a member: invisible
    assert client.get(f"/pilots/{t['pilotId']}", headers=VIEW).status_code == 404
    pilot = client.get(f"/pilots/{t['pilotId']}", headers=ADMIN).json()
    assert {k["key"] for k in pilot["kpis"]} == {
        "gate_wait_s",
        "peak_queue_veh",
        "gate_throughput_vph",
        "reports_resolved_pct",
    }
    assert pilot["progress"]["days"] == 60


@needs_db
def test_onboarding_refuses_invented_junctions_and_bad_input(client, made):
    base = {"name": f"Test bad {uuid.uuid4().hex[:6]}", "kind": "police", "pilot": {"name": "p"}}
    assert (
        client.post(
            "/tenants", headers=ADMIN, json={**base, "sites": [{"id": "J09", "name": "New"}]}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/tenants",
            headers=ADMIN,
            json={**base, "sites": [{"id": "J05", "name": "x"}], "dataSources": ["MADE-UP"]},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/tenants",
            headers=ADMIN,
            json={
                **base,
                "sites": [{"id": "J05", "name": "x"}],
                "pilot": {"name": "p", "start": "2026-10-01"},
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/tenants", headers=OPER, json={**base, "sites": [{"id": "J05", "name": "x"}]}
        ).status_code
        == 403
    )
    t = onboard(client, made)
    dup = client.post(
        "/tenants",
        headers=ADMIN,
        json={
            **base,
            "name": client.get(f"/tenants/{t['id']}", headers=ADMIN).json()["name"],
            "sites": [{"id": "J05", "name": "x"}],
        },
    )
    assert dup.status_code == 409


@needs_db
def test_kpi_values_need_a_source(client, made):
    t = onboard(client, made)
    pid = t["pilotId"]
    kpi = next(
        k for k in client.get(f"/pilots/{pid}", headers=OPER).json()["kpis"] if k["key"] == "red_wait_s"
    )
    url = f"/pilots/{pid}/kpis/{kpi['id']}"
    assert client.patch(url, headers=OPER, json={"current": {"value": 40}}).status_code == 422
    assert client.patch(
        url, headers=VIEW, json={"current": {"value": 40, "source": "FIELD"}}
    ).status_code in (403, 404)
    r = client.patch(
        url,
        headers=OPER,
        json={
            "baseline": {"value": 50, "source": "FIELD", "note": "stopwatch"},
            "current": {"value": 40, "source": "FIELD"},
        },
    ).json()
    assert (
        r["baseline"]["value"] == 50
        and r["current"]["source"] == "FIELD"
        and r["change"] == {"abs": -10, "pct": -20.0}
    )


@needs_db
def test_notes_feedback_reviews_changes_and_evidence(client, made):
    t = onboard(client, made)
    tid, pid = t["id"], t["pilotId"]
    n = client.post(
        f"/tenants/{tid}/notes",
        headers=OPER,
        json={
            "siteId": "J05",
            "approach": "Mansarover Metro",
            "text": "Queue spills back at 18:30",
            "pinned": True,
        },
    )
    assert n.status_code == 201 and n.json()["pinned"]
    assert (
        client.post(
            f"/tenants/{tid}/notes", headers=OPER, json={"siteId": "J01", "text": "not in this tenant"}
        ).status_code
        == 422
    )
    assert client.post(
        f"/tenants/{tid}/notes", headers=VIEW, json={"siteId": "J05", "text": "x"}
    ).status_code in (403, 404)
    assert client.patch(
        f"/tenants/{tid}/notes/{n.json()['id']}", headers=OPER, json={"resolved": True}
    ).json()["resolved"]

    member = H("member@test.local", "Viewer")
    for useful in (True, False):  # voting again changes the vote
        assert (
            client.post(
                f"/tenants/{tid}/feedback",
                headers=member,
                json={"insight": "audit.top-fixes", "page": "audit", "useful": useful},
            ).status_code
            == 201
        )
    fb = client.get(f"/tenants/{tid}/feedback", headers=member).json()
    assert fb["total"] == {"useful": 0, "notUseful": 1} and fb["mine"] == {"audit.top-fixes": False}
    assert (
        client.post(
            f"/tenants/{tid}/feedback", headers=member, json={"insight": "bad key!", "useful": True}
        ).status_code
        == 422
    )

    ans = {
        "daysUsed": 4,
        "mostUseful": "audit",
        "actionTaken": True,
        "actionNote": "Asked for stopwatch timings at J05",
        "missing": "Night-time view",
        "rating": 4,
    }
    r = client.post(f"/pilots/{pid}/reviews", headers=OPER, json={"weekStart": "2026-09-24", "answers": ans})
    assert r.json()["weekStart"] == "2026-09-21"  # stored against the Monday
    assert (
        client.post(
            f"/pilots/{pid}/reviews",
            headers=OPER,
            json={"weekStart": "2026-09-24", "answers": {**ans, "rating": 6}},
        ).status_code
        == 422
    )

    future = (today() + timedelta(days=5)).isoformat()
    assert (
        client.post(
            f"/tenants/{tid}/timing-changes",
            headers=OPER,
            json={"siteId": "J05", "changedOn": future, "before": "a", "after": "b"},
        ).status_code
        == 422
    )
    ch = client.post(f"/tenants/{tid}/timing-changes", headers=OPER, json={"siteId": "J05", "changedOn": "2026-09-20", "timeWindow": "17:00-20:00",
                                                                             "before": "Main 45 s / cross 45 s", "after": "Main 60 s / cross 30 s", "reason": "Main road 80% of PCU"})  # fmt: skip
    assert ch.status_code == 201 and ch.json()["source"] == "FIELD"

    ev = client.get(f"/pilots/{pid}/evidence", headers=OPER).json()
    assert ev["tenant"]["reportTemplate"]["sections"] == ["kpis", "notes", "sources"]
    assert "stops_per_trip" in ev["placeholders"]
    assert (
        ev["reviews"]["count"] == 1
        and ev["reviews"]["avgRating"] == 4
        and ev["reviews"]["actions"][0]["note"].startswith("Asked")
    )
    assert len(ev["changes"]) == 1 and len(ev["notes"]) == 1 and "never changed any signal" in ev["readOnly"]


@needs_db
def test_archiving_hides_a_tenant_but_keeps_it(client, made):
    t = onboard(client, made, kind="campus")
    assert client.patch(f"/tenants/{t['id']}", headers=OPER, json={"archived": True}).status_code == 403
    assert client.patch(f"/tenants/{t['id']}", headers=ADMIN, json={"archived": True}).json() == {
        "id": t["id"],
        "archived": True,
    }
    assert t["id"] not in {x["id"] for x in client.get("/tenants", headers=ADMIN).json()["tenants"]}
    assert client.get(f"/pilots/{t['pilotId']}", headers=ADMIN).status_code == 404
    assert client.patch("/tenants/jaipur-police", headers=ADMIN, json={"archived": True}).status_code == 422
