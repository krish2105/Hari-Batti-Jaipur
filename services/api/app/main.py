"""HariBatti API: REST + WebSocket for the website, the police dashboard and the mobile app.

Read-only by design: it reads signal phases from a PhaseSource (the simulator today) and survey
data from the project's data files / Postgres. No route can send a command to a traffic signal.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import db_available
from .live import LiveHub
from .routers import admin, audit, auth_routes, copilot, corridor, events, junctions, plans, reports, signals
from .sources.sim import SimSource

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = settings()
    hub = LiveHub(SimSource(s.redis_url, s.redis_channel), record=db_available())
    app.state.hub = hub
    hub.start()
    yield
    await hub.stop()


app = FastAPI(
    title="HariBatti API",
    description=(
        "Read-only signal countdown + audit API for the Mansarovar corridor (J01–J08), Jaipur. "
        "Every number carries its source: SIM, FIELD, SURVEY, CROWD or ITMS."
    ),
    version="0.3.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings().cors_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)
for r in (junctions, corridor, signals, plans, copilot, reports, audit, events, auth_routes, admin):
    app.include_router(r.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Simple liveness check used by `make api` verification and by the apps."""
    return {"status": "ok", "service": "haribatti-api"}


@app.get("/status")
def status() -> dict:
    """What is connected: database, live signal source."""
    return {"database": db_available(), "signals": app.state.hub.status()}
