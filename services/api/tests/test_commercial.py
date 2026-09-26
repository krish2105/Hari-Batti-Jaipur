"""Commercial surfaces (P8 W17): the website pilot-request form (spam checks) and usage metering."""

import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete

from app import metering, ratelimit
from app.auth import make_token
from tests.conftest import needs_db

ADMIN = {"Authorization": f"Bearer {make_token('admin@test.local', 'Admin')}"}


def lead(**kw) -> dict:
    return {"name": "Test Person", "organisation": f"Test Org {uuid.uuid4().hex[:6]}", "email": "person@example.test", "offer": "pilot",
            "city": "Jaipur", "message": "Pilot on 8 junctions", "consent": True, "website": "", "startedAt": time.time() * 1000 - 20_000, **kw}  # fmt: skip


@needs_db
def test_pilot_request_is_stored_and_spam_is_refused(client):
    from app.db import connect
    from app.tables import leads

    ratelimit.reset()
    good = lead()
    try:
        r = client.post("/leads", json=good)
        assert r.status_code == 201 and r.json()["received"]
        assert (
            client.post("/leads", json=lead(website="http://spam.example")).status_code == 422
        )  # honeypot filled
        assert (
            client.post("/leads", json=lead(startedAt=time.time() * 1000)).status_code == 422
        )  # filled in 0 s
        assert client.post("/leads", json=lead(consent=False)).status_code == 422
        assert client.post("/leads", json=lead(email="not-an-email")).status_code == 422
        stored = client.get("/leads", headers=ADMIN).json()["leads"]
        assert any(x["organisation"] == good["organisation"] and x["status"] == "new" for x in stored)
        assert (
            client.get(
                "/leads", headers={"Authorization": f"Bearer {make_token('v@test.local', 'Viewer')}"}
            ).status_code
            == 403
        )
        for _ in range(5):
            client.post("/leads", json=lead())
        assert client.post("/leads", json=lead()).status_code == 429  # 5 per IP per hour
    finally:
        ratelimit.reset()
        with connect() as c:
            c.execute(delete(leads).where(leads.c.organisation.like("Test Org %")))


def test_metering_attributes_calls_to_tenants():
    email = f"meter-{uuid.uuid4().hex[:6]}@test.local"
    h = f"Bearer {make_token(email, 'Viewer')}"
    metering._counts.clear()
    metering.count("/tenants/campus-demo-sim/notes", h)
    metering.count("/tenants/campus-demo-sim/notes", h)
    metering.count("/health", h)  # probes are not billed
    metering.count("/junctions", "")  # anonymous calls are not billed
    today = datetime.now(UTC).date()
    assert metering._counts[(today, "campus-demo-sim", email)] == 2
    assert sum(metering._counts.values()) == 2
    metering._counts.clear()


@needs_db
def test_metering_report_and_csv(client):
    from app.db import connect
    from app.tables import usage_daily

    email = f"meter-{uuid.uuid4().hex[:6]}@test.local"
    h = {"Authorization": f"Bearer {make_token(email, 'Viewer')}"}
    try:
        for _ in range(3):
            client.get("/tenants/jaipur-police", headers=h)
        month = datetime.now(UTC).strftime("%Y-%m")
        rows = {
            r["tenantId"]: r for r in client.get(f"/metering?month={month}", headers=ADMIN).json()["tenants"]
        }
        assert rows["jaipur-police"]["apiCalls"] >= 3 and rows["jaipur-police"]["sitesActive"] == 8
        csv = client.get(f"/metering.csv?month={month}", headers=ADMIN)
        assert csv.headers["content-type"].startswith("text/csv") and csv.text.startswith(
            "month,tenantId,tenant,kind"
        )
        assert client.get("/metering?month=2026-13", headers=ADMIN).status_code == 422
    finally:
        with connect() as c:
            c.execute(delete(usage_daily).where(usage_daily.c.email.like("meter-%@test.local")))
