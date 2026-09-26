"""API behaviour: health, junction data from the registry, read-only guarantee, auth, reports."""

import pytest

from app.main import app
from app.routers.events import EVENTS
from app.sources.sim import parse_message
from tests.conftest import needs_db

CONTROL_WORDS = ("control", "command", "setphase", "set_phase", "override", "switch", "actuate", "hold")


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "service": "haribatti-api"}


def test_no_route_can_control_a_signal():
    """Acceptance check: nothing in the API sends commands to signals."""
    for path, ops in app.openapi()["paths"].items():
        assert not any(w in path.lower() for w in CONTROL_WORDS), path
        assert set(ops) <= {"get", "post", "patch"}, path
    posts = {p for p, ops in app.openapi()["paths"].items() if "post" in ops}
    assert posts == {
        "/plans/simulate",
        "/copilot/ask",
        "/reports",
        "/events/green-corridor",
        "/audit/event",
        "/auth/otp/request",
        "/auth/otp/verify",
        "/connectors/preview",  # pure mapping preview over pasted sample records (P8 W12)
        # P8 W13: pilot records typed in by people (none of them reaches a signal)
        "/tenants",
        "/tenants/{tenant_id}/notes",
        "/tenants/{tenant_id}/feedback",
        "/tenants/{tenant_id}/timing-changes",
        "/pilots/{pilot_id}/reviews",
        "/privacy/requests",  # P8 W16: a person asks for their data to be erased or corrected
        "/auth/logout",  # P8 W16: server-side sign-out
        "/leads",  # P8 W17: pilot / contact request from the website form
    }


def test_junctions_come_from_the_registry(client):
    js = client.get("/junctions").json()
    assert [j["id"] for j in js] == [f"J0{i}" for i in range(1, 9)]
    j04 = next(j for j in js if j["id"] == "J04")
    assert {a["name"] for a in j04["approaches"]} == {
        "Durgapur",
        "Mansarover Metro",
        "Mohanpura",
        "Sanganer Stadium",
    }
    assert j04["survey"][0]["sourceLabel"] == "Survey, May 2026"
    assert j04["survey"][0]["totalVeh"] == 129_047  # docs/05-data-analysis.md, 11 May
    assert j04["timing"] == "ASSUMED"


def test_pending_positions_are_not_drawn(client):
    j08 = client.get("/junctions/J08").json()
    assert j08["positionStatus"] in ("PENDING", "REGISTRY", "CANDIDATE")
    if j08["positionStatus"] == "PENDING":
        assert j08["lat"] is None and j08["lng"] is None


def test_unknown_junction_404(client):
    assert client.get("/junctions/J09").status_code == 404


def test_parse_message_accepts_only_sim_phase_states():
    ok = (
        '{"junctionId":"J03","approachId":"J03-x","colour":"GREEN","secondsRemaining":5,'
        '"confidence":0.9,"source":"SIM","updatedAt":"2026-09-26T00:00:00Z"}'
    )
    assert parse_message(ok)["colour"] == "GREEN"
    assert parse_message(ok.replace('"SIM"', '"ITMS"')) is None  # SimSource only trusts SIM
    assert parse_message(ok.replace("GREEN", "BLUE")) is None
    assert parse_message("not json") is None


def test_green_corridor_is_a_recommendation(client, token):
    body = {"junctions": ["J03", "J04", "J05"], "speed_kmh": 36, "spacing_m": 500}
    assert client.post("/events/green-corridor", json=body).status_code == 401  # dashboard only (W16)
    r = client.post("/events/green-corridor", json=body, headers={"Authorization": f"Bearer {token}"}).json()
    assert [h["arriveAfterS"] for h in r["holds"]] == [0, 50, 100]  # 500 m at 10 m/s
    assert "never" in r["note"].lower()
    assert len(EVENTS) == 4


def test_protected_routes_need_sign_in(client):
    assert client.post("/copilot/ask", json={"question": "which junction is worst?"}).status_code == 401
    assert client.post("/plans/simulate", json={}).status_code == 401


def test_viewer_cannot_run_plan_studio(client):
    from app.auth import make_token

    tok = make_token("viewer@test.local", "Viewer")
    r = client.post("/plans/simulate", json={}, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403


@needs_db
def test_otp_login_flow(client):
    r = client.post("/auth/otp/request", json={"email": "Officer@Test.local"}).json()
    assert r["sent"] and len(r["devCode"]) == 6
    bad = client.post("/auth/otp/verify", json={"email": "officer@test.local", "code": "000000"})
    if r["devCode"] != "000000":
        assert bad.status_code == 401
    ok = client.post("/auth/otp/verify", json={"email": "officer@test.local", "code": r["devCode"]}).json()
    assert ok["role"] == "Viewer"
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {ok['token']}"}).json()
    assert me == {"email": "officer@test.local", "role": "Viewer"}
    # a used code cannot be used again
    again = client.post("/auth/otp/verify", json={"email": "officer@test.local", "code": r["devCode"]})
    assert again.status_code == 401


@needs_db
def test_citizen_report_groups_by_nearest_junction(client, token):
    # 50 m from the J05 candidate position (Madhyam Marg x Patel Marg)
    r = client.post("/reports", json={"type": "broken", "lat": 26.8526, "lng": 75.7674}).json()
    assert r["junctionId"] == "J05" and r["status"] == "New"
    listing = client.get("/reports", headers={"Authorization": f"Bearer {token}"}).json()
    assert any(g["group_key"] == "J05:broken" for g in listing["groups"])
    ch = client.patch(
        f"/reports/{r['id']}", json={"status": "Assigned"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert ch.json()["status"] == "Assigned"


@pytest.mark.parametrize(
    "bad", [{"type": "broken", "lat": 19.07, "lng": 72.87}, {"type": "fire", "lat": 26.85, "lng": 75.76}]
)
def test_report_validation(client, bad):
    assert client.post("/reports", json=bad).status_code == 422


@needs_db
def test_login_is_audited_and_admin_can_read(client):
    r = client.post("/auth/otp/request", json={"email": "audit@test.local"}).json()
    client.post("/auth/otp/verify", json={"email": "audit@test.local", "code": r["devCode"]})
    from app.auth import make_token

    admin_tok = make_token("admin@test.local", "Admin")
    events = client.get("/audit/log", headers={"Authorization": f"Bearer {admin_tok}"}).json()["events"]
    assert any(e["action"] == "login" and e["email"] == "audit@test.local" for e in events)
    viewer_tok = make_token("v@test.local", "Viewer")
    assert client.get("/audit/log", headers={"Authorization": f"Bearer {viewer_tok}"}).status_code == 403


def test_analytics_names_are_allow_listed(client):
    assert client.get("/analytics/../../etc/passwd").status_code == 404
    assert client.get("/analytics/unknown").status_code == 404
    assert client.get("/analytics/forecast").status_code == 200


@needs_db
def test_metric_hours_are_clock_hours(client):
    """J01's AM peak (09:00 in the survey summary) must be labelled 09:00, not 17:00."""
    res = client.get("/junctions/J01/metrics", params={"date": "2026-05-11"})
    if res.status_code == 404:  # CI: no confidential tmc_clean.csv, so no hourly metrics were computed
        pytest.skip("hourly metrics need data/processed/tmc_clean.csv (local only)")
    hours = res.json()["hours"]
    assert all(h["hour_start"] == f"{h['hour']:02d}:00" for h in hours)
    busiest = max(hours, key=lambda h: h["flow_pcu_h"])
    assert busiest["hour_start"] in ("09:00", "10:00", "18:00", "19:00")


def test_plan_library_summarises_the_sim_plans(client):
    lib = client.get("/plans/library").json()
    if not lib["available"]:
        pytest.skip("no sim build")
    j = lib["plans"]["demand2"]["junctions"]["J05"]
    assert j["cycleS"] == sum(p["durationS"] for p in j["phases"])
    assert lib["spacingSource"] == "ASSUMED"
