"""Junction video intake (P8 W15): upload checks (type, signature, size), roles, camera-profile
validation and the timings proposal. The CV job itself (PyTorch) is not started in tests."""

import json

from sqlalchemy import delete

from app.auth import make_token
from app.routers import video
from tests.conftest import needs_db

OPER = {"Authorization": f"Bearer {make_token('operator@test.local', 'Operator')}"}
VIEW = {"Authorization": f"Bearer {make_token('viewer@test.local', 'Viewer')}"}
MP4_HEAD = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


def test_magic_bytes():
    assert video.magic_ok("mp4", MP4_HEAD)
    assert video.magic_ok("webm", b"\x1a\x45\xdf\xa3\x01\x00")
    assert video.magic_ok("avi", b"RIFF\x00\x00\x00\x00AVI LIST")
    assert not video.magic_ok("mp4", b"<html><script>")
    assert not video.magic_ok("exe", b"MZ\x90\x00")


def profile(**kw) -> video.Profile:
    base = {"date": "2026-10-05", "start_clock": "18:15",
            "approaches": {"W": {"name": "Mansarover Metro", "polygon": [[0, 0], [100, 0], [100, 100]], "count_line": [[10, 10], [90, 10]]}},
            "stop_line": {"approach": "W", "line": [[10, 50], [90, 50]]}, "lamp_roi": [200, 20, 10, 20], "lamp_approach": "W"}  # fmt: skip
    return video.Profile(**{**base, **kw})


def test_profile_validation():
    assert video.validate_profile(profile(), 1080, 606, "J05") == []
    errs = video.validate_profile(
        profile(approaches={"W": {"name": "Nowhere Road", "polygon": [[0, 0], [5000, 0], [100, 100]]}}),
        1080,
        606,
        "J05",
    )
    assert any("not an approach" in e for e in errs) and any("inside" in e for e in errs)
    assert video.validate_profile(profile(lamp_roi=[1075, 600, 10, 10]), 1080, 606, "J05")
    assert video.validate_profile(
        profile(approaches={"X": {"name": "Mansarover Metro", "polygon": [[0, 0], [1, 0], [1, 1]]}}),
        1080,
        606,
        "J05",
    )


def test_upload_needs_an_operator(client):
    assert client.post("/video/uploads?junction=J05&filename=a.mp4", content=MP4_HEAD).status_code == 401
    assert (
        client.post("/video/uploads?junction=J05&filename=a.mp4", content=MP4_HEAD, headers=VIEW).status_code
        == 403
    )


@needs_db
def test_upload_rejects_wrong_type_or_content(client):
    assert (
        client.post("/video/uploads?junction=J05&filename=a.exe", content=b"MZ", headers=OPER).status_code
        == 415
    )
    assert (
        client.post(
            "/video/uploads?junction=J05&filename=a.mp4", content=b"<html>not a video</html>", headers=OPER
        ).status_code
        == 415
    )
    assert (
        client.post("/video/uploads?junction=J09&filename=a.mp4", content=MP4_HEAD, headers=OPER).status_code
        == 422
    )
    assert not list(video.UPLOADS.glob("*.exe")) if video.UPLOADS.exists() else True


@needs_db
def test_upload_profile_and_proposal_flow(client, monkeypatch, tmp_path):
    from app.db import connect
    from app.tables import video_jobs

    async def fake_probe(job_id, raw):  # the real probe runs services/cv (OpenCV + PyTorch)
        (video.UPLOADS / job_id).mkdir(parents=True, exist_ok=True)
        video._set(
            job_id,
            status="ready",
            probe={
                "ok": True,
                "width": 1080,
                "height": 606,
                "fps": 25,
                "quality": {"ok": True, "warnings": []},
            },
        )

    monkeypatch.setattr(video, "_probe", fake_probe)
    monkeypatch.setattr(video, "UPLOADS", tmp_path / "uploads")
    monkeypatch.setattr(video, "PROPOSED", tmp_path / "signal_timings.proposed.csv")
    r = client.post("/video/uploads?junction=J05&filename=clip.mp4", content=MP4_HEAD, headers=OPER)
    assert r.status_code == 201
    jid = r.json()["id"]
    try:
        assert client.get(f"/video/uploads/{jid}", headers=OPER).json()["status"] == "ready"
        bad = client.patch(
            f"/video/uploads/{jid}/profile",
            headers=OPER,
            json={**json.loads(profile().model_dump_json()), "lamp_roi": [2000, 0, 5, 5]},
        )
        assert bad.status_code == 422
        ok = client.patch(
            f"/video/uploads/{jid}/profile", headers=OPER, json=json.loads(profile().model_dump_json())
        )
        assert ok.status_code == 200 and ok.json()["profile"]["junction"] == "J05"
        assert (
            client.post(f"/video/uploads/{jid}/timings-proposal", headers=OPER).status_code == 409
        )  # nothing measured yet
        out = video.UPLOADS / jid
        (out / "signal_timings_field.csv").write_text(
            "junction_id,date,time_window,phase_no,approaches_served,green_s,amber_s,all_red_s,cycle_s,signal_mode,notes\nJ05,2026-10-05,18:15-18:25,1,Mansarover Metro,52,3,,,FIXED,measured\n"
        )
        video._set(jid, status="done", summary={"quality": {"ok": True}})
        p = client.post(f"/video/uploads/{jid}/timings-proposal", headers=OPER).json()
        assert p["rows"] == 1 and "REVIEW" in video.PROPOSED.read_text()
        assert client.get(f"/video/uploads/{jid}/outputs/../../etc/passwd", headers=OPER).status_code == 404
        assert (
            client.get(f"/video/uploads/{jid}/outputs/signal_timings_field.csv", headers=OPER).status_code
            == 200
        )
        assert client.get("/video/uploads/nothex/frame", headers=OPER).status_code == 404
    finally:
        with connect() as c:
            c.execute(delete(video_jobs).where(video_jobs.c.id == jid))
