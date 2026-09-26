"""HariBatti API: REST + WebSocket for the website, the police dashboard and the mobile app.

Read-only by design: it reads signal phases from a PhaseSource (the simulator today) and survey
data from the project's data files / Postgres. No route can send a command to a traffic signal.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import metering
from .config import settings
from .connectors.source import ConnectorSource, load_connectors
from .db import db_available
from .live import LiveHub
from .routers import (
    admin,
    audit,
    auth_routes,
    commercial,
    connectors,
    copilot,
    corridor,
    events,
    junctions,
    monitor,
    pilot,
    plans,
    privacy,
    reports,
    signals,
    study,
    video,
)
from .sources.sim import SimSource

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("haribatti.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = settings()
    if s.environment == "production" and (problems := s.production_problems()):
        raise RuntimeError("Refusing to start in production: " + "; ".join(problems))
    app.state.connectors = {}
    try:
        app.state.connectors = load_connectors(overrides=connectors.saved_mappings())
    except (OSError, KeyError, ValueError) as e:  # a broken config must not stop the API
        log.error("config/connectors.yaml not usable (%s); staying on the simulator", e)
    if s.signal_source != "sim" and s.signal_source in app.state.connectors:
        source = ConnectorSource(app.state.connectors[s.signal_source])
        log.info("live feed: connector %s (%s)", s.signal_source, source.name)
    else:
        if s.signal_source != "sim":
            log.error(
                "SIGNAL_SOURCE=%s is not in config/connectors.yaml; using the simulator", s.signal_source
            )
        source = SimSource(s.redis_url, s.redis_channel)
    hub = LiveHub(source, record=db_available())
    app.state.hub = hub
    hub.start()
    from .monitor import Monitor

    app.state.monitor = Monitor(hub, record=db_available())
    app.state.monitor.start()
    daily = asyncio.create_task(_retention_daily(), name="retention") if db_available() else None
    meter = asyncio.create_task(metering.run(), name="metering") if db_available() else None
    yield
    if daily:
        daily.cancel()
    if meter:
        meter.cancel()
        metering.flush()
    await app.state.monitor.stop()
    await hub.stop()


async def _retention_daily() -> None:
    """Delete expired personal data once a day (app/jobs/retention.py); failures are logged, not fatal."""
    from .jobs import retention

    while True:
        try:
            await asyncio.to_thread(retention.run)
        except Exception:
            log.exception("retention job failed")
        await asyncio.sleep(24 * 3600)


app = FastAPI(
    title="HariBatti API",
    description=(
        "Read-only signal countdown + audit API for the Mansarovar corridor (J01–J08), Jaipur. "
        "Every number carries its source: SIM, FIELD, SURVEY, CROWD or ITMS."
    ),
    version="0.3.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def json_errors(request: Request, call_next):
    """Turn an unexpected error into a JSON 500. Registered before CORS, so it runs inside it and the
    reply keeps its CORS headers (otherwise the browser reports a 500 as "API not reachable")."""
    try:
        return await call_next(request)
    except Exception:  # last-resort handler: details go to the log, not the client
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            {"detail": "Internal error in the HariBatti API (see the API log)."}, status_code=500
        )


# Security headers on every reply (OWASP ASVS 14.4). The API only serves JSON, so the CSP forbids everything
# except the interactive /docs page, which loads Swagger UI from jsDelivr.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site",
}
API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
DOCS_CSP = ("default-src 'none'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; frame-ancestors 'none'")  # fmt: skip


@app.middleware("http")
async def security_headers(request: Request, call_next):
    metering.count(request.url.path, request.headers.get("authorization", ""))  # P8 W17 usage metering
    response = await call_next(request)
    for k, v in SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    docs = request.url.path in ("/docs", "/redoc", "/docs/oauth2-redirect")
    response.headers.setdefault("Content-Security-Policy", DOCS_CSP if docs else API_CSP)
    if request.url.path.startswith("/auth"):
        response.headers["Cache-Control"] = "no-store"  # never cache sign-in replies or tokens
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings().cors_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)
for r in (
    junctions,
    corridor,
    signals,
    plans,
    copilot,
    reports,
    audit,
    events,
    auth_routes,
    admin,
    connectors,
    pilot,
    privacy,
    monitor,
    commercial,
    study,
    video,
):
    app.include_router(r.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Simple liveness check used by `make api` verification and by the apps."""
    return {"status": "ok", "service": "haribatti-api"}


@app.get("/status")
def status() -> dict:
    """What is connected: database, live signal source."""
    return {"database": db_available(), "signals": app.state.hub.status()}
