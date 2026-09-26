"""Health, readiness, metrics, alerts and the uptime ledger (P8 W11).

/health  - the process is up (liveness)
/ready   - it can serve: database and Redis answer (readiness; 503 otherwise)
/metrics - Prometheus text format for any scraper (counts only, no personal data)
/monitor/* - open and recent alerts, current service status, daily uptime % (signed-in users)
"""

import time

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select

from .. import monitor
from ..auth import viewer
from ..db import connect, db_available
from ..tables import alerts

router = APIRouter(tags=["monitor"])
STARTED = time.time()


@router.get("/ready")
def ready(request: Request) -> JSONResponse:
    checks = {"database": db_available(), "redis": monitor.redis_ok()}
    return JSONResponse(
        {"ready": all(checks.values()), "checks": checks}, status_code=200 if all(checks.values()) else 503
    )


def _status(request: Request) -> dict:
    mon = getattr(request.app.state, "monitor", None)
    hub = request.app.state.hub
    return {
        "api": True,
        "database": db_available(),
        "redis": monitor.redis_ok(),
        "signal_feed": bool(mon and mon.feed_fresh()),
        "feedSource": hub.source.name,
        "messagesReceived": hub.received,
        "uptimeS": round(time.time() - STARTED),
        "websocket": request.app.state.broadcast.status()
        if hasattr(request.app.state, "broadcast")
        else None,
    }


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(request: Request) -> str:
    s = _status(request)
    lines = [
        "# HELP haribatti_up 1 when a component answers", "# TYPE haribatti_up gauge",
        *[f'haribatti_up{{component="{k}"}} {int(bool(s[k]))}' for k in monitor.SERVICES],
        "# HELP haribatti_feed_messages_total PhaseState messages received", "# TYPE haribatti_feed_messages_total counter",
        f'haribatti_feed_messages_total{{source="{s["feedSource"]}"}} {s["messagesReceived"]}',
        "# HELP haribatti_process_uptime_seconds Seconds since the API started", "# TYPE haribatti_process_uptime_seconds gauge",
        f"haribatti_process_uptime_seconds {s['uptimeS']}",
        "# HELP haribatti_ws_clients Connected WebSocket clients", "# TYPE haribatti_ws_clients gauge",
        f"haribatti_ws_clients {(s['websocket'] or {}).get('clients', 0)}",
        "# HELP haribatti_ws_frames_skipped_total Frames skipped for slow clients", "# TYPE haribatti_ws_frames_skipped_total counter",
        f"haribatti_ws_frames_skipped_total {(s['websocket'] or {}).get('framesSkipped', 0)}",
    ]  # fmt: skip
    mon = getattr(request.app.state, "monitor", None)
    if mon:
        lines += [
            "# HELP haribatti_open_alerts Alerts open now",
            "# TYPE haribatti_open_alerts gauge",
            f"haribatti_open_alerts {len(mon.rules.open)}",
        ]
    return "\n".join(lines) + "\n"


@router.get("/monitor/status")
def status(request: Request, _user: dict = Depends(viewer)) -> dict:
    mon = getattr(request.app.state, "monitor", None)
    return {
        **_status(request),
        "openAlerts": sorted(mon.rules.open) if mon else [],
        "staleAfterS": monitor.STALE_S,
    }


@router.get("/monitor/alerts")
def list_alerts(limit: int = Query(100, ge=1, le=500), _user: dict = Depends(viewer)) -> dict:
    if not db_available():
        return {"alerts": []}
    with connect() as c:
        rows = c.execute(select(alerts).order_by(alerts.c.opened_at.desc()).limit(limit)).all()
    return {"alerts": [{"id": r.id, "key": r.key, "kind": r.kind, "source": r.source, "junctionId": r.junction_id, "message": r.message,
                        "openedAt": r.opened_at.isoformat(), "closedAt": r.closed_at.isoformat() if r.closed_at else None} for r in rows]}  # fmt: skip


@router.get("/monitor/uptime")
def uptime(days: int = Query(30, ge=1, le=90), _user: dict = Depends(viewer)) -> dict:
    return (
        monitor.uptime_days(days)
        if db_available()
        else {"days": days, "services": {}, "overall": {}, "goalPct": 99.0}
    )
