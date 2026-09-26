"""Security readiness (P8 W16): access matrix built from every route, security headers, production
refusal, rate limits, the copilot's database role, data-subject requests and retention."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import insert, select, text
from sqlalchemy.exc import DBAPIError

from app import ratelimit
from app.auth import make_token
from app.config import DEV_SECRET, Settings, settings
from app.main import app
from tests.conftest import needs_db

PUBLIC_WRITES = {
    ("POST", "/auth/otp/request"),
    ("POST", "/auth/otp/verify"),
    ("POST", "/reports"),
    ("POST", "/leads"),
    ("POST", "/study/enrol"),  # protected by the invite code instead of a sign-in
}
ORDER = ("Viewer", "Operator", "Admin")


def required_role(route: APIRoute) -> str | None:
    """The role a route demands (from auth.require), or None when it is public."""
    stack = list(route.dependant.dependencies)
    while stack:
        d = stack.pop()
        if role := getattr(d.call, "required_role", None):
            return role
        if getattr(d.call, "__name__", "") == "current_user":
            return "Viewer"
        stack.extend(d.dependencies)
    return None


def _flat(rs):
    """Every APIRoute, also inside included routers (FastAPI >= 0.140 keeps them nested)."""
    for r in rs:
        if isinstance(r, APIRoute):
            yield r
        elif hasattr(r, "original_router"):
            yield from _flat(r.original_router.routes)


def routes():
    for r in _flat(app.routes):
        for m in r.methods - {"HEAD", "OPTIONS"}:
            yield m, r


def fill(path: str) -> str:
    return (
        path.replace("{job_id}", "0123456789abcdef")
        .replace("{name}", "counts.csv")
        .replace("{junction_id}", "J05")
        .replace("{id}", "J05")
        .replace("{tenant_id}", "jaipur-police")
        .replace("{connector_id}", "x")
        .replace("{", "")
        .replace("}", "")
    )


def test_every_write_needs_a_role_except_the_public_ones():
    open_writes = {(m, r.path) for m, r in routes() if m != "GET" and required_role(r) is None}
    assert open_writes == PUBLIC_WRITES


@pytest.mark.parametrize("role", ["Viewer", "Operator"])
def test_access_matrix(client, role):
    """A signed-in user below a route's role gets 403, and nobody unsigned gets through."""
    h = {"Authorization": f"Bearer {make_token(f'{role.lower()}@matrix.test', role)}"}
    checked = 0
    for m, r in routes():
        need = required_role(r)
        if need is None:
            continue
        url = fill(r.path)
        assert client.request(m, url, json={}).status_code == 401, (m, r.path)
        if need not in ORDER:  # study routes take a study token, never an officer session
            assert client.request(m, url, json={}, headers=h).status_code in (401, 403), (m, r.path)
            continue
        if ORDER.index(role) < ORDER.index(need):
            assert client.request(m, url, json={}, headers=h).status_code == 403, (m, r.path, role)
            checked += 1
    assert checked > 5


def test_security_headers(client):
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["content-security-policy"].startswith("default-src 'none'")
    assert "strict-transport-security" not in r.headers  # plain http on a laptop
    assert (
        "strict-transport-security" in client.get("/health", headers={"x-forwarded-proto": "https"}).headers
    )
    assert "cdn.jsdelivr.net" in client.get("/docs").headers["content-security-policy"]
    assert (
        client.post("/auth/otp/verify", json={"email": "a@b.co", "code": "000000"}).headers["cache-control"]
        == "no-store"
    )


def test_production_refuses_development_settings():
    dev = Settings(environment="production", jwt_secret=DEV_SECRET, auth_dev_echo_otp=True, auth_open_signup=True,
                   cors_origins="http://localhost:3001", admin_emails="")  # fmt: skip
    assert len(dev.production_problems()) == 5
    prod = Settings(environment="production", jwt_secret="x" * 48, auth_dev_echo_otp=False, auth_open_signup=False,
                    cors_origins="https://dashboard.example.in", admin_emails="dcp@example.in")  # fmt: skip
    assert prod.production_problems() == []


def test_ip_rate_limit():
    ratelimit.reset()
    for _ in range(3):
        ratelimit.hit("t", "1.2.3.4", limit=3, window_s=60)
    with pytest.raises(Exception) as e:
        ratelimit.hit("t", "1.2.3.4", limit=3, window_s=60)
    assert e.value.status_code == 429 and int(e.value.headers["Retry-After"]) > 0
    ratelimit.hit("t", "5.6.7.8", limit=3, window_s=60)  # other callers are not affected
    ratelimit.reset()


@needs_db
def test_otp_codes_per_email_are_limited(client, monkeypatch):
    monkeypatch.setattr(settings(), "otp_max_per_email_15min", 2)
    email = f"limit-{uuid.uuid4().hex[:8]}@test.local"
    assert client.post("/auth/otp/request", json={"email": email}).status_code == 200
    assert client.post("/auth/otp/request", json={"email": email}).status_code == 200
    r = client.post("/auth/otp/request", json={"email": email})
    assert r.status_code == 429 and r.headers["retry-after"] == "900"


@needs_db
def test_copilot_role_cannot_read_private_tables():
    from app.db import _copilot_role, read_only

    if not _copilot_role():
        pytest.skip("copilot_reader role not available (no CREATEROLE)")
    with read_only() as c:
        assert c.execute(text("SELECT count(*) FROM copilot_metrics")).scalar() >= 0
    for table in ("users", "otp_codes", "audit_log", "tenants"):
        with pytest.raises(Exception, match="permission denied"), read_only() as c:
            c.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
    with (
        pytest.raises(DBAPIError, match="read-only transaction|permission denied"),
        read_only() as c,
    ):  # no writes either
        c.execute(text("INSERT INTO junctions (id) VALUES ('J99')"))


@needs_db
def test_export_and_erase_my_data(client):
    email = f"dsr-{uuid.uuid4().hex[:8]}@test.local"
    me = {"Authorization": f"Bearer {make_token(email, 'Viewer')}"}
    admin = {"Authorization": f"Bearer {make_token('admin@test.local', 'Admin')}"}
    first = client.get("/privacy/me/export", headers=me).json()
    assert first["email"] == email and "audit_log" in first["data"]
    assert (
        len(client.get("/privacy/me/export", headers=me).json()["data"]["audit_log"]) >= 1
    )  # the first export was logged
    rid = client.post(
        "/privacy/requests", headers=me, json={"kind": "erase", "note": "leaving the pilot"}
    ).json()["id"]
    assert client.get("/privacy/requests", headers=me).status_code == 403
    done = client.patch(f"/privacy/requests/{rid}", headers=admin, json={"status": "done"}).json()
    assert done["rowsAnonymised"] >= 1
    after = client.get("/privacy/me/export", headers=me).json()["data"]
    assert after["audit_log"] == [
        e for e in after["audit_log"] if e["action"] == "privacy_export"
    ]  # only the new export
    assert client.patch(f"/privacy/requests/{rid}", headers=admin, json={"status": "done"}).status_code == 409


@needs_db
def test_retention_deletes_expired_data():
    from app.db import connect
    from app.jobs import retention
    from app.tables import audit_log, otp_codes

    tag = f"retention-{uuid.uuid4().hex[:8]}@test.local"
    now = datetime.now(UTC)
    with connect() as c:
        c.execute(insert(otp_codes).values(email=tag, code_hash="x", expires_at=now - timedelta(days=2)))
        c.execute(insert(otp_codes).values(email=tag, code_hash="y", expires_at=now + timedelta(minutes=5)))
        c.execute(insert(audit_log).values(email=tag, action="login", ts=now - timedelta(days=400)))
        c.execute(insert(audit_log).values(email=tag, action="login", ts=now - timedelta(days=10)))
    out = retention.run(now)
    assert out["otp_codes"] >= 1 and out["audit_log"] >= 1
    with connect() as c:
        assert [r.code_hash for r in c.execute(select(otp_codes).where(otp_codes.c.email == tag))] == ["y"]
        assert len(c.execute(select(audit_log).where(audit_log.c.email == tag)).all()) == 1


@needs_db
def test_logout_revokes_the_token(client):
    h = {"Authorization": f"Bearer {make_token(f'logout-{uuid.uuid4().hex[:6]}@test.local', 'Viewer')}"}
    assert client.get("/auth/me", headers=h).status_code == 200
    assert client.post("/auth/logout", headers=h).json() == {"signedOut": True}
    assert client.get("/auth/me", headers=h).status_code == 401


@needs_db
def test_console_code_and_email_delivery(client, monkeypatch):
    from app import auth

    email = f"console-{uuid.uuid4().hex[:6]}@test.local"
    code = auth.issue_code(email)  # open signup in tests: a Viewer
    ok = client.post("/auth/otp/verify", json={"email": email, "code": code})
    assert ok.status_code == 200 and ok.json()["email"] == email
    sent = []
    monkeypatch.setattr(settings(), "smtp_host", "smtp.example.test")
    monkeypatch.setattr(auth, "send_code_email", lambda e, c: sent.append((e, c)) or True)
    r = client.post("/auth/otp/request", json={"email": f"mail-{uuid.uuid4().hex[:6]}@test.local"}).json()
    assert r["delivery"] == "email" and r["sent"] is True and len(sent) == 1 and sent[0][1].isdigit()
