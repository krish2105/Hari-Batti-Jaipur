"""Data connectors (P8 W12): read-only contract, mapping, replay, SPaT, file drop, timing import,
malformed input (fuzz), clock drift and the Admin routes. All inputs are synthetic fixtures."""

import asyncio
import inspect
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app.auth import make_token
from app.connectors import base, file_drop, http_poll, mqtt_sub, replay, spat, timing_import, ws_push
from app.connectors.base import Mapping, ReadOnlyConnector
from app.connectors.source import ConnectorSource, build, load_connectors, validate_mapping

FX = Path(__file__).parent / "fixtures" / "connectors"
DEMO = {"tenant": "demo", "source": "ITMS", "fields": {"junction": "site", "approach": "arm", "colour": "state", "remaining": "secs_left", "timestamp": "ts"},
        "colour_values": {"R": "RED", "Y": "AMBER", "G": "GREEN"}, "ids": {"SIG-105/1": "J05-mansarover-metro", "SIG-105/3": "J05-sanganer-stadium"}}  # fmt: skip
WRITE_WORDS = (
    "write",
    "send",
    "publish",
    "post",
    "put",
    "patch",
    "delete",
    "control",
    "command",
    "set_phase",
    "setphase",
    "override",
    "actuate",
    "switch",
)
ALL_CLASSES = [ReadOnlyConnector, http_poll.HttpPollConnector, ws_push.WebSocketConnector, mqtt_sub.MqttConnector,
               file_drop.FileDropConnector, replay.ReplayConnector, spat.SpatConnector]  # fmt: skip


def mapping(**kw) -> Mapping:
    from app.connectors.source import make_mapping

    return make_mapping({**DEMO, **kw})


async def take(conn: ReadOnlyConnector, n: int, timeout: float = 5.0) -> list[dict]:
    out: list[dict] = []

    async def run():
        async for ps in conn.stream():
            out.append(ps)
            if len(out) >= n:
                return

    await asyncio.wait_for(run(), timeout)
    return out


# ---- the read-only guarantee ---------------------------------------------------------------------


@pytest.mark.parametrize("cls", ALL_CLASSES, ids=lambda c: c.__name__)
def test_no_connector_exposes_a_write_method(cls):
    """Fails if anyone adds a public method that could send something to a signal or a vendor system."""
    public = {n for n, _ in inspect.getmembers(cls, callable) if not n.startswith("_")}
    assert public <= {"connect", "stream", "history", "health"}, public
    assert not [n for n in public if any(w in n.lower() for w in WRITE_WORDS)]


def test_http_connector_only_ever_sends_get():
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req.method)
        return httpx.Response(
            200, json={"data": {"signals": [{"site": "SIG-105", "arm": 1, "state": "G", "secs_left": 12}]}}
        )

    conn = http_poll.HttpPollConnector("t", mapping(), "http://vendor.test/live", every_s=0.01, records_path="data.signals",
                                       transport=httpx.MockTransport(handler))  # fmt: skip
    got = asyncio.run(take(conn, 3))
    assert {m["approachId"] for m in got} == {"J05-mansarover-metro"}
    assert set(seen) == {"GET"}


def test_mqtt_connector_never_publishes():
    src = inspect.getsource(mqtt_sub)
    assert ".publish(" not in src and "subscribe(" in src


# ---- mapping --------------------------------------------------------------------------------------


def test_mapping_contract_matches_phasestate():
    ps = mapping().apply(
        {"site": "SIG-105", "arm": 3, "state": "R", "secs_left": "41.26", "ts": "2026-09-01T12:00:00Z"}
    )
    assert ps is not None
    assert {
        "junctionId",
        "approachId",
        "colour",
        "secondsRemaining",
        "confidence",
        "source",
        "updatedAt",
    } <= set(ps)
    assert (
        ps["junctionId"] == "J05"
        and ps["colour"] == "RED"
        and ps["secondsRemaining"] == 41.3
        and ps["source"] == "ITMS"
    )


def test_mapping_validation_rejects_invented_junctions():
    assert validate_mapping(DEMO) == []
    errs = validate_mapping({**DEMO, "ids": {"X/1": "J09-nowhere", "Y/1": "bad id"}})
    assert any("J09" in e for e in errs) and any("bad id" in e for e in errs)
    assert validate_mapping(
        {**DEMO, "source": "SIM"}
    )  # a live feed can never be labelled as simulated data...
    assert (
        validate_mapping({**DEMO, "source": "SIM"}, "replay") == []
    )  # ...only a recorded synthetic replay can


def test_fuzz_malformed_records_never_raise():
    m = mapping()
    rnd = random.Random(7)
    junk = [None, 1, "x", [], {}, {"site": None}, {"site": "SIG-105", "arm": 1, "state": "G", "secs_left": "nan?"},
            {"site": "SIG-105", "arm": 1, "state": "G", "secs_left": -3}, {"site": "SIG-105", "arm": 1, "state": "purple", "secs_left": 3},
            {"site": "SIG-105", "arm": 1, "state": "G", "secs_left": 1e9}, {"site": {"a": 1}, "arm": [1], "state": 2, "secs_left": True}]  # fmt: skip
    for _ in range(500):
        junk.append(
            {
                k: rnd.choice([None, "", "G", 1, -1, 3.5, "SIG-105", {}, [], "2026-13-45"])
                for k in ("site", "arm", "state", "secs_left", "ts")
            }
        )
    for rec in junk:
        ps = m.apply(rec)
        assert ps is None or (ps["colour"] in base.COLOURS and 0 <= ps["secondsRemaining"] < 3600)


# ---- replay, clock drift, health ------------------------------------------------------------------


def test_replay_maps_the_recorded_feed_and_counts_rejects():
    conn = replay.ReplayConnector("demo", mapping(), FX / "vendor_feed.jsonl", speed=0)
    got = asyncio.run(take(conn, 240))
    assert len(got) == 240 and {m["approachId"] for m in got} == {
        "J05-mansarover-metro",
        "J05-sanganer-stadium",
    }
    assert {m["colour"] for m in got} == {"RED", "AMBER", "GREEN"}
    h = conn.health()
    assert h["readOnly"] is True and h["received"] == 240


def test_clock_drift_is_reported():
    """The fixture is timestamped 2026-09-01: far from now, so health must warn about the clock."""
    conn = replay.ReplayConnector("demo", mapping(), FX / "vendor_feed.jsonl", speed=0)
    asyncio.run(take(conn, 5))
    assert conn.health()["clockDriftS"] > base.DRIFT_WARN_S
    assert any("clock" in w for w in conn.health()["warnings"])


def test_small_drift_is_not_a_warning():
    now = datetime.now(UTC)
    rows = [
        {
            "t": 0,
            "msg": {
                "site": "SIG-105",
                "arm": 1,
                "state": "G",
                "secs_left": 9,
                "ts": (now - timedelta(seconds=0.5)).isoformat(),
            },
        }
    ]
    p = Path(FX.parent / "_tmp_feed.jsonl")
    p.write_text("\n".join(json.dumps(r) for r in rows))
    try:
        conn = replay.ReplayConnector("d", mapping(), p, speed=0)
        asyncio.run(take(conn, 1))
        assert conn.health()["clockDriftS"] < base.DRIFT_WARN_S
        assert not any("clock" in w for w in conn.health()["warnings"])
    finally:
        p.unlink()


def test_epoch_timestamps_are_understood():
    assert (
        base.parse_ts(1788264000) == base.parse_ts(1788264000000) == datetime.fromtimestamp(1788264000, UTC)
    )
    assert base.parse_ts("garbage") is None


def test_replay_retime_makes_a_demo_look_live():
    conn = replay.ReplayConnector("demo", mapping(), FX / "vendor_feed.jsonl", speed=0, retime=True)
    asyncio.run(take(conn, 5))
    assert conn.health()["clockDriftS"] < base.DRIFT_WARN_S


def test_config_with_a_bad_mapping_is_refused():
    with pytest.raises(ValueError, match="J09"):
        build(
            {
                "id": "x",
                "kind": "replay",
                "path": "nowhere.jsonl",
                "mapping": {**DEMO, "ids": {"a/1": "J09-x"}},
            }
        )


def test_connector_source_is_a_phasesource():
    src = ConnectorSource(replay.ReplayConnector("demo", mapping(), FX / "vendor_feed.jsonl", speed=0))
    assert src.name == "ITMS"

    async def first():
        async for ps in src.stream():
            return ps

    assert asyncio.run(first())["source"] == "ITMS"


# ---- SPaT -----------------------------------------------------------------------------------------


def test_spat_decoding():
    msg = json.loads((FX / "spat.json").read_text())
    now = datetime(2026, 9, 1, 12, 5, 0, tzinfo=UTC)  # TimeMark 3000 = 5 min into the hour
    recs = spat.decode(msg, now)
    by = {r["approach"]: r for r in recs}
    assert set(by) == {2, 4}  # dark group 6 and unknown time (36001) on group 8 are skipped
    assert by[2]["colour"] == "green" and by[2]["remaining"] == 0.0
    assert by[4]["colour"] == "red" and by[4]["remaining"] == 35.0
    assert spat.mark_seconds(10, datetime(2026, 9, 1, 12, 59, 59, tzinfo=UTC)) == 2.0  # wraps at the hour


def test_spat_fuzz():
    for bad in [
        {},
        {"intersections": None},
        {"intersections": [1, "x", {"states": [None, {"state-time-speed": "x"}]}]},
    ]:
        assert spat.decode(bad) == []


# ---- file drop and timing import -----------------------------------------------------------------


def test_file_drop_reads_csv_and_excel(tmp_path):
    from openpyxl import Workbook

    (tmp_path / "a.csv").write_text((FX / "export.csv").read_text())
    wb = Workbook()
    wb.active.append(["Junction", "Arm", "Signal", "Seconds Left", "Time"])
    wb.active.append(["J05", 1, "Red", 20, "2026-09-01T12:01:00Z"])
    wb.save(tmp_path / "b.xlsx")
    m = mapping(fields={"junction": "Junction", "approach": "Arm", "colour": "Signal", "remaining": "Seconds Left", "timestamp": "Time"},
                ids={"J05/1": "J05-mansarover-metro"}, colour_values={})  # fmt: skip
    conn = file_drop.FileDropConnector("f", m, tmp_path, every_s=0.01)
    got = asyncio.run(take(conn, 3))
    assert [g["colour"] for g in got] == ["GREEN", "AMBER", "RED"]
    assert conn.rejected == 1  # the "blue" row
    assert conn._new_files() == []  # files are read once and never touched
    assert (tmp_path / "a.csv").exists() and (tmp_path / "b.xlsx").exists()


def test_timing_import_proposes_rows_and_flags_problems():
    rows, problems = timing_import.propose(
        timing_import.read_any(FX / "timing_plan.csv"), timing_import.known_junctions()
    )
    assert [r["junction_id"] for r in rows] == ["J05", "J05", "J05"]
    assert rows[0]["green_s"] == 50 and rows[0]["amber_s"] == 3 and rows[0]["signal_mode"] == "FIXED"
    assert all(r["notes"].startswith("IMPORTED") for r in rows)
    assert any("J09" in p for p in problems)  # never invented
    assert not any("adds up" in p for p in problems)  # 55 + 50 + 15 = 120


def test_timing_import_reads_pdf_tables(tmp_path):
    pytest.importorskip("pdfplumber")
    # a tiny one-table PDF drawn by hand (lines + text) so pdfplumber can find the grid
    rows = [
        ["Junction", "Phase", "Green", "Amber", "All Red", "Cycle"],
        ["J04", "1", "60", "3", "2", "130"],
        ["J04", "2", "60", "3", "2", "130"],
    ]
    pdf = _table_pdf(rows)
    (tmp_path / "plan.pdf").write_bytes(pdf)
    got, problems = timing_import.propose(
        timing_import.read_any(tmp_path / "plan.pdf"), timing_import.known_junctions()
    )
    assert [r["green_s"] for r in got] == [60, 60] and not problems


def _table_pdf(rows: list[list[str]]) -> bytes:
    """A minimal PDF with a ruled table (no PDF library needed to write it)."""
    w, h, x0, y0 = 70, 20, 40, 700
    ops = ["0.5 w"]
    for i in range(len(rows) + 1):
        ops.append(f"{x0} {y0 - i * h} m {x0 + w * len(rows[0])} {y0 - i * h} l S")
    for j in range(len(rows[0]) + 1):
        ops.append(f"{x0 + j * w} {y0} m {x0 + j * w} {y0 - h * len(rows)} l S")
    for i, r in enumerate(rows):
        for j, cell in enumerate(r):
            ops.append(f"BT /F1 9 Tf {x0 + j * w + 4} {y0 - (i + 1) * h + 6} Td ({cell}) Tj ET")
    stream = "\n".join(ops).encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]  # fmt: skip
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(
        b"%010d 00000 n \n" % o for o in offs
    )
    return out + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)


# ---- config and routes ----------------------------------------------------------------------------


def test_example_config_builds_every_kind():
    conns = load_connectors(Path(__file__).parents[3] / "config/connectors.example.yaml")
    assert {c.kind for c in conns.values()} == {
        "replay",
        "http_poll",
        "websocket",
        "mqtt",
        "file_drop",
        "spat",
    }
    with pytest.raises(ValueError):
        build({"id": "x", "kind": "telnet", "mapping": DEMO})


def _admin():
    return {"Authorization": f"Bearer {make_token('admin@test.local', 'Admin')}"}


def test_connector_routes_need_admin(client, token):
    assert client.get("/connectors").status_code == 401
    assert client.get("/connectors", headers={"Authorization": f"Bearer {token}"}).status_code == 403
    r = client.get("/connectors", headers=_admin())
    assert r.status_code == 200 and r.json()["readOnly"] is True
    assert "url" not in json.dumps(r.json()["connectors"]).lower()  # endpoints stay private


def test_preview_maps_samples_without_side_effects(client):
    sample = [
        {"site": "SIG-105", "arm": 1, "state": "G", "secs_left": 12},
        {"site": "SIG-105", "arm": 9, "state": "G", "secs_left": 12},
    ]
    r = client.post("/connectors/preview", headers=_admin(), json={"mapping": DEMO, "sample": sample}).json()
    assert (
        r["counts"] == {"mapped": 1, "rejected": 1} and r["mapped"][0]["approachId"] == "J05-mansarover-metro"
    )
    bad = client.post(
        "/connectors/preview",
        headers=_admin(),
        json={"mapping": {**DEMO, "ids": {"a/1": "J42-x"}}, "sample": sample},
    ).json()
    assert bad["errors"]
    sp = client.post("/connectors/preview", headers=_admin(),
                     json={"mapping": {**DEMO, "ids": {"105/2": "J05-mansarover-metro"}}, "sample": json.loads((FX / "spat.json").read_text()), "format": "spat"}).json()  # fmt: skip
    assert sp["counts"]["mapped"] == 1


def test_patch_mapping_validates(client):
    r = client.patch(
        "/connectors/demo-replay/mapping", headers=_admin(), json={**DEMO, "ids": {"x/1": "J99-nope"}}
    )
    assert r.status_code in (404, 422)  # 404 when config/connectors.yaml is absent on this machine
