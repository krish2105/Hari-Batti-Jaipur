"""Live signal phases: latest snapshot and a WebSocket stream (source always shown)."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["signals"])


@router.get("/signals/latest")
def latest(request: Request, junction: str | None = None) -> dict:
    hub = request.app.state.hub
    states = hub.snapshot()
    if junction:
        states = [s for s in states if s["junctionId"] == junction.upper()]
    return {"status": hub.status(), "states": states}


@router.get("/signals/history/{junction_id}")
async def history(request: Request, junction_id: str, minutes: int = Query(10, ge=1, le=240)) -> dict:
    end = datetime.now(UTC)
    rows = await request.app.state.hub.source.history(
        junction_id.upper(), end - timedelta(minutes=minutes), end
    )
    return {"junctionId": junction_id.upper(), "events": rows}


@router.websocket("/ws/signals")
async def ws_signals(ws: WebSocket) -> None:
    """The current snapshot, then a batch of the newest states every 0.5 s (app/broadcast.py).
    ?junction=J05 or ?junctions=J03,J04,J05 limits the stream to those junctions (what an app needs)."""
    raw = ws.query_params.get("junctions") or ws.query_params.get("junction") or ""
    ids = frozenset(j.strip().upper() for j in raw.split(",") if j.strip())
    if len(ids) > 50:
        await ws.close(code=1008)
        return
    await ws.accept()
    b = ws.app.state.broadcast
    key = ids or None
    await ws.send_text(b.snapshot_text(key))
    conn = b.add(ws, key)
    try:
        while True:  # clients only listen; this waits for the close
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        b.remove(conn)
