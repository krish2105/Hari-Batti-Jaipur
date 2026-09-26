"""WebSocket fan-out (P8 W10): snapshot first, then batched newest states, filtered per subscription."""

import time
from datetime import UTC, datetime

from app.main import app


def ps(jid: str, ap: str, colour: str, rem: int) -> dict:
    return {"junctionId": jid, "approachId": ap, "colour": colour, "secondsRemaining": rem, "confidence": 0.9, "source": "SIM",
            "updatedAt": datetime.now(UTC).isoformat()}  # fmt: skip


def inject(msgs: list[dict]) -> None:
    """Hand messages to the hub's queues on the app's own event loop (asyncio queues are not thread-safe)."""
    hub = app.state.hub
    loop = app.state.broadcast._task.get_loop()
    for m in msgs:
        hub.latest[m["approachId"]] = m
        for q in list(hub.subscribers):
            loop.call_soon_threadsafe(q.put_nowait, m)


def test_snapshot_then_filtered_batches(client):
    task = app.state.broadcast._task
    assert task is not None and not task.done(), (
        f"broadcaster stopped: {task.exception() if task and task.done() else None}"
    )
    inject([ps("J05", "J05-a", "RED", 30), ps("J04", "J04-a", "GREEN", 10)])
    with client.websocket_connect("/ws/signals?junctions=J05") as ws:
        snap = ws.receive_json()
        assert snap["type"] == "snapshot" and {s["junctionId"] for s in snap["states"]} == {"J05"}
        time.sleep(0.1)
        inject(
            [ps("J04", "J04-a", "RED", 50), ps("J05", "J05-a", "RED", 29), ps("J05", "J05-a", "GREEN", 40)]
        )
        frame = ws.receive_json()
        assert frame["type"] == "states"
        assert [(s["approachId"], s["colour"]) for s in frame["states"]] == [
            ("J05-a", "GREEN")
        ]  # newest only, J05 only
    assert app.state.broadcast.status()["clients"] == 0  # the closed socket was removed


def test_too_many_junctions_is_refused(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/ws/signals?junctions=" + ",".join(f"X{i}" for i in range(60))) as ws,
    ):
        ws.receive_json()
