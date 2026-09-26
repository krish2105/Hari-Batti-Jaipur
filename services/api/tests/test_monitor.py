"""Monitoring (P8 W11): freshness rules with a fake clock, alert storage, routes and the uptime ledger."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, insert

from app.auth import make_token
from app.monitor import MIN_GREEN_S, STALE_S, FreshnessRules, uptime_days
from tests.conftest import needs_db


def ps(ap: str, colour: str = "RED", rem: float = 20, source: str = "SIM") -> dict:
    return {
        "junctionId": ap[:3],
        "approachId": ap,
        "colour": colour,
        "secondsRemaining": rem,
        "source": source,
    }


def test_stale_feed_opens_within_a_minute_and_clears():
    r = FreshnessRules()
    r.observe(ps("J05-a"), now=0)
    assert r.evaluate(now=STALE_S - 1) == []
    ev = r.evaluate(now=STALE_S + 5)  # the monitor evaluates every 5 s -> alert by ~35 s, well under 60 s
    assert [(e.kind, e.opened) for e in ev if e.kind == "feed_stale"] == [("feed_stale", True)]
    assert r.evaluate(now=STALE_S + 10) == []  # opens once, not every tick
    r.observe(ps("J05-a"), now=STALE_S + 12)
    assert [(e.kind, e.opened) for e in r.evaluate(now=STALE_S + 13) if e.kind == "feed_stale"] == [
        ("feed_stale", False)
    ]


def test_one_dark_junction_while_the_feed_is_alive():
    r = FreshnessRules()
    r.observe(ps("J04-a"), now=0)
    r.observe(ps("J05-a"), now=0)
    for t in range(5, 60, 5):
        r.observe(ps("J05-a"), now=t)  # J05 keeps talking, J04 went silent at t=0
    dark = [e for e in r.evaluate(now=60) if e.kind == "junction_dark"]
    assert [(e.junction, e.opened) for e in dark] == [("J04", True)]


def test_impossible_values():
    r = FreshnessRules()
    assert r.observe(ps("J05-a", rem=-3), now=0)[0].kind == "impossible"
    assert r.observe(ps("J05-a", rem=900), now=1)[0].kind == "impossible"
    r.observe(ps("J05-b", "GREEN"), now=10)
    short = r.observe(ps("J05-b", "AMBER"), now=10 + MIN_GREEN_S - 1)
    assert short and "green lasted" in short[0].message
    r.observe(ps("J05-c", "GREEN"), now=20)
    assert r.observe(ps("J05-c", "AMBER"), now=45) == []  # a normal 25 s green is fine


def test_health_ready_metrics(client):
    assert client.get("/health").json()["status"] == "ok"
    r = client.get("/ready")
    assert r.status_code in (200, 503) and set(r.json()["checks"]) == {"database", "redis"}
    m = client.get("/metrics").text
    assert 'haribatti_up{component="api"} 1' in m and "haribatti_feed_messages_total" in m
    assert client.get("/monitor/status").status_code == 401
    h = {"Authorization": f"Bearer {make_token('viewer@test.local', 'Viewer')}"}
    st = client.get("/monitor/status", headers=h).json()
    assert st["api"] is True and st["staleAfterS"] == STALE_S


@needs_db
def test_uptime_ledger_daily_percentages():
    from app.db import connect
    from app.tables import uptime_checks

    svc = f"test-{uuid.uuid4().hex[:6]}"
    now = datetime.now(UTC)
    rows = [
        {"service": svc, "ok": i != 0, "ts": now - timedelta(minutes=i)} for i in range(4)
    ]  # 3 of 4 ok today
    rows += [{"service": svc, "ok": True, "ts": now - timedelta(days=1, minutes=i)} for i in range(2)]
    try:
        with connect() as c:
            c.execute(insert(uptime_checks), rows)
        out = uptime_days(7)
        days = {d["day"]: d["uptimePct"] for d in out["services"][svc]}
        assert (
            days[now.date().isoformat()] == 75.0
            and days[(now - timedelta(days=1)).date().isoformat()] == 100.0
        )
        assert out["overall"][svc] == round((75 * 4 + 100 * 2) / 6, 2) and out["goalPct"] == 99.0
    finally:
        with connect() as c:
            c.execute(delete(uptime_checks).where(uptime_checks.c.service == svc))
