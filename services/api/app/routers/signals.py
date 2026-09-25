"""Live signal phases: latest snapshot and a WebSocket stream (source always shown)."""

import asyncio
import contextlib
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
    """Sends the current snapshot, then every PhaseState as it arrives (optionally one junction)."""
    await ws.accept()
    hub = ws.app.state.hub
    junction = (ws.query_params.get("junction") or "").upper() or None
    q = hub.subscribe()
    try:
        await ws.send_json(
            {
                "type": "snapshot",
                "states": [s for s in hub.snapshot() if not junction or s["junctionId"] == junction],
            }
        )
        while True:
            batch = [await q.get()]
            with contextlib.suppress(asyncio.QueueEmpty):
                while len(batch) < 64:
                    batch.append(q.get_nowait())
            batch = [m for m in batch if not junction or m["junctionId"] == junction]
            if batch:
                await ws.send_json({"type": "states", "states": batch})
    except WebSocketDisconnect:
        pass
    finally:
        hub.unsubscribe(q)
