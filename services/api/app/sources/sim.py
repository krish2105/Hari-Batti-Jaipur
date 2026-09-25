"""SimSource: reads the simulator's PhaseState JSON from Redis channel "signals" (make sim)."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime

import redis.asyncio as aioredis
from sqlalchemy import select

from .. import db
from ..tables import phase_events
from .base import PhaseState

log = logging.getLogger("haribatti.sim")
REQUIRED = ("junctionId", "approachId", "colour", "secondsRemaining", "confidence", "source", "updatedAt")


def parse_message(raw: bytes | str) -> PhaseState | None:
    """Validate one Redis message. Returns None for anything that is not a SIM PhaseState."""
    try:
        msg = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(msg, dict) or any(k not in msg for k in REQUIRED) or msg.get("source") != "SIM":
        return None
    if msg["colour"] not in ("RED", "AMBER", "GREEN", "FLASHING_AMBER"):
        return None
    return msg


class SimSource:
    name = "SIM"

    def __init__(self, redis_url: str, channel: str = "signals"):
        self.redis_url = redis_url
        self.channel = channel

    async def stream(self) -> AsyncIterator[PhaseState]:
        """Subscribe and yield messages forever; reconnects with backoff when Redis goes away."""
        backoff = 1.0
        while True:
            try:
                client = aioredis.from_url(self.redis_url)
                pubsub = client.pubsub()
                await pubsub.subscribe(self.channel)
                log.info("SimSource subscribed to %s on %s", self.channel, self.redis_url)
                backoff = 1.0
                async for item in pubsub.listen():
                    if item.get("type") != "message":
                        continue
                    if (msg := parse_message(item["data"])) is not None:
                        yield msg
            except (OSError, aioredis.RedisError) as e:
                log.warning("Redis not reachable (%s); retry in %.0fs — is `make infra` running?", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    async def history(self, junction_id: str, start: datetime, end: datetime) -> list[PhaseState]:
        """Colour changes stored by the API while it listened (phase_events table)."""

        def _query() -> list[PhaseState]:
            q = (
                select(phase_events)
                .where(phase_events.c.junction_id == junction_id)
                .where(phase_events.c.start_ts >= start, phase_events.c.start_ts <= end)
                .order_by(phase_events.c.start_ts)
            )
            with db.connect() as c:
                return [
                    {
                        "junctionId": r.junction_id,
                        "approachId": r.approach_id,
                        "colour": r.colour,
                        "startTs": r.start_ts.isoformat(),
                        "endTs": r.end_ts.isoformat() if r.end_ts else None,
                        "source": r.source,
                        "simClock": r.sim_clock,
                    }
                    for r in c.execute(q)
                ]

        return await asyncio.to_thread(_query)
