"""LiveHub: keeps the latest PhaseState per approach, records colour changes, feeds WebSockets.

Runs as one background task inside the API. Read-only: it only listens to the PhaseSource.
"""

import asyncio
import contextlib
import logging
from datetime import UTC, datetime

from sqlalchemy import insert, update

from . import db
from .sources.base import PhaseSource, PhaseState
from .tables import phase_events

log = logging.getLogger("haribatti.live")


class LiveHub:
    def __init__(self, source: PhaseSource, record: bool = True):
        self.source = source
        self.latest: dict[str, PhaseState] = {}  # approachId -> latest message
        self.last_colour: dict[str, tuple[str, int | None]] = {}  # approachId -> (colour, open event id)
        self.subscribers: set[asyncio.Queue] = set()
        self.record = record
        self.received = 0
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="live-hub")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers.discard(q)

    def snapshot(self) -> list[PhaseState]:
        return sorted(self.latest.values(), key=lambda m: m["approachId"])

    def status(self) -> dict:
        newest = max((m["updatedAt"] for m in self.latest.values()), default=None)
        return {
            "source": self.source.name,
            "approaches": len(self.latest),
            "received": self.received,
            "newest": newest,
            "recording": self.record,
        }

    async def _run(self) -> None:
        async for msg in self.source.stream():
            self.received += 1
            self.latest[msg["approachId"]] = msg
            for q in list(self.subscribers):
                if q.full():  # slow client: drop its oldest message rather than block everyone
                    with contextlib.suppress(asyncio.QueueEmpty):
                        q.get_nowait()
                q.put_nowait(msg)
            if self.record:
                await self._record_change(msg)

    async def _record_change(self, msg: PhaseState) -> None:
        """Write a phase_events row when an approach changes colour (closing the previous one)."""
        prev = self.last_colour.get(msg["approachId"])
        if prev and prev[0] == msg["colour"]:
            return
        now = datetime.now(UTC)

        def _write() -> int | None:
            with db.connect() as c:
                if prev and prev[1] is not None:
                    c.execute(update(phase_events).where(phase_events.c.id == prev[1]).values(end_ts=now))
                res = c.execute(
                    insert(phase_events)
                    .values(
                        junction_id=msg["junctionId"],
                        approach_id=msg["approachId"],
                        colour=msg["colour"],
                        start_ts=now,
                        source=msg["source"],
                        sim_clock=msg.get("simClock"),
                    )
                    .returning(phase_events.c.id)
                )
                return res.scalar_one()

        try:
            event_id = await asyncio.to_thread(_write)
        except Exception as e:  # noqa: BLE001 - DB down must not stop the live feed
            log.debug("phase event not recorded: %s", e)
            event_id = None
        self.last_colour[msg["approachId"]] = (msg["colour"], event_id)
