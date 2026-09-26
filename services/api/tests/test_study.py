"""Field study kit (P8 W14): trimming, randomisation, invite-only enrolment, upload and withdrawal."""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, insert, select

from app import ratelimit, study
from app.auth import make_token
from tests.conftest import needs_db

ADMIN = {"Authorization": f"Bearer {make_token('admin@test.local', 'Admin')}"}


def line(n: int, step_m: float = 10.0, lat0: float = 26.85, lng0: float = 75.76) -> list[list[float]]:
    """n points 1 s apart going north `step_m` metres a time (about 36 km/h)."""
    return [[1_000.0 + i, lat0 + i * step_m / 111_320, lng0, 36.0] for i in range(n)]


def test_trim_removes_200_m_at_each_end():
    pts = line(151)  # 1,500 m
    kept = study.trim(pts)
    assert kept and study.haversine_m((pts[0][1], pts[0][2]), (kept[0][1], kept[0][2])) >= 199
    assert study.haversine_m((kept[-1][1], kept[-1][2]), (pts[-1][1], pts[-1][2])) >= 199
    assert 109 <= len(kept) <= 111  # about 1,100 m in the middle, 10 m apart
    assert study.trim(line(40)) == []  # 390 m: nothing may be kept


def test_permuted_blocks_keep_the_arms_balanced():
    rnd = random.Random(3)
    arms: list[str] = []
    for _ in range(20):
        arms.append(study.next_arm(arms, rnd))  # type: ignore[arg-type]
    assert arms.count("advice") == arms.count("control") == 10
    assert all({arms[i], arms[i + 1]} == {"advice", "control"} for i in range(0, 20, 2))


def test_trace_validation():
    assert study.validate(line(10))
    assert study.validate([[1, 999, 75.7, 30]] * 40)
    back = line(40)
    back[5][0] = back[4][0]
    assert "increase" in study.validate(back)
    assert study.validate(line(40)) is None


@needs_db
def test_invite_enrol_run_upload_and_withdraw(client):
    from app.db import connect
    from app.tables import study_invites, study_participants

    ratelimit.reset()
    code = client.post(
        "/study/invites", headers=ADMIN, json={"label": "test cohort", "maxParticipants": 2}
    ).json()["code"]
    pids = []
    try:
        assert (
            client.post(
                "/study/enrol", json={"code": "WRONGCODE", "vehicle": "car", "consent": True}
            ).status_code
            == 403
        )
        assert (
            client.post("/study/enrol", json={"code": code, "vehicle": "car", "consent": False}).status_code
            == 422
        )
        me = client.post("/study/enrol", json={"code": code, "vehicle": "scooter", "consent": True}).json()
        pids.append(me["participantId"])
        assert me["participantId"].startswith("P-")
        h = {"Authorization": f"Bearer {me['token']}"}
        assert (
            client.post("/study/runs", headers=ADMIN).status_code == 401
        )  # an officer session is not a study token
        r1, r2 = client.post("/study/runs", headers=h).json(), client.post("/study/runs", headers=h).json()
        assert {r1["arm"], r2["arm"]} == {"advice", "control"}
        up = client.post(
            f"/study/runs/{r1['runId']}/trace", headers=h, json={"points": line(151), "direction": "east"}
        ).json()
        assert (
            up["runId"] == r1["runId"]
            and 109 <= up["pointsKept"] <= 111
            and up["pointsKept"] + up["pointsTrimmed"] == 151
        )
        assert (
            client.post(
                f"/study/runs/{r1['runId']}/trace", headers=h, json={"points": line(151), "direction": "east"}
            ).status_code
            == 409
        )
        assert (
            client.post(
                f"/study/runs/{r2['runId']}/trace", headers=h, json={"points": line(40), "direction": "east"}
            ).status_code
            == 422
        )
        exported = [
            r
            for r in client.get("/study/export", headers=ADMIN).json()["runs"]
            if r["participant"] == me["participantId"]
        ]
        assert (
            len(exported) == 1
            and exported[0]["arm"] == r1["arm"]
            and len(exported[0]["points"]) == up["pointsKept"]
        )
        assert client.post("/study/withdraw", headers=h).json()["withdrawn"] is True
        assert client.post("/study/runs", headers=h).status_code == 403
        assert not [
            r
            for r in client.get("/study/export", headers=ADMIN).json()["runs"]
            if r["participant"] == me["participantId"]
        ]
        pids.append(
            client.post("/study/enrol", json={"code": code, "vehicle": "car", "consent": True}).json()[
                "participantId"
            ]
        )
        assert (
            client.post("/study/enrol", json={"code": code, "vehicle": "car", "consent": True}).status_code
            == 403
        )  # invite full
    finally:
        ratelimit.reset()
        with connect() as c:
            for pid in pids:
                c.execute(delete(study_participants).where(study_participants.c.id == pid))
            c.execute(delete(study_invites).where(study_invites.c.label == "test cohort"))


@needs_db
def test_retention_deletes_traces_after_30_days():
    from app.db import connect
    from app.jobs import retention
    from app.tables import study_participants, study_runs, study_traces

    pid = study.new_participant_id()
    with connect() as c:
        c.execute(insert(study_participants).values(id=pid, vehicle="car", invite_hash="x"))
        rid = c.execute(
            insert(study_runs).values(participant_id=pid, arm="advice").returning(study_runs.c.id)
        ).scalar_one()
        c.execute(
            insert(study_traces).values(
                run_id=rid, points=[[1, 2, 3, 4]], created_at=datetime.now(UTC) - timedelta(days=31)
            )
        )
    try:
        assert retention.run()["study_traces"] >= 1
        with connect() as c:
            assert c.execute(select(study_traces).where(study_traces.c.run_id == rid)).first() is None
    finally:
        with connect() as c:
            c.execute(delete(study_participants).where(study_participants.c.id == pid))
