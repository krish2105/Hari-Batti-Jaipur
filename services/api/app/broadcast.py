"""WebSocket fan-out for many clients (P8 W10).

Before: every PhaseState went into every client's own queue and was serialised once per client,
so 1,600 messages/s x N clients of work; at 1,000 clients the API used a whole CPU and half the
clients could not connect. Now one task collects messages for TICK_S, keeps only the newest state
per approach, serialises each frame ONCE per subscription (all junctions, or a set of junctions) and
sends the same text to every client with that subscription. A client that is still busy receiving
the previous frame skips this one (it gets the newest state next tick) instead of slowing everyone.
"""

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass, field

from fastapi import WebSocket

log = logging.getLogger("haribatti.broadcast")
TICK_S = 0.5


@dataclass(eq=False)
class Conn:
    ws: WebSocket
    key: frozenset[str] | None  # None = every junction
    busy: bool = False
    skipped: int = 0


@dataclass
class Broadcaster:
    hub: object
    conns: set[Conn] = field(default_factory=set)
    frames_sent: int = 0
    frames_skipped: int = 0
    _task: asyncio.Task | None = None
    _snapshot: dict = field(default_factory=dict)  # subscription key -> cached snapshot text for this tick

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="broadcast")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    def snapshot_text(self, key: frozenset[str] | None) -> str:
        """The current snapshot for a subscription, serialised at most once per tick."""
        if key not in self._snapshot:
            states = [s for s in self.hub.snapshot() if key is None or s["junctionId"] in key]
            self._snapshot[key] = json.dumps({"type": "snapshot", "states": states}, separators=(",", ":"))
        return self._snapshot[key]

    def add(self, ws: WebSocket, key: frozenset[str] | None) -> Conn:
        c = Conn(ws, key)
        self.conns.add(c)
        return c

    def remove(self, c: Conn) -> None:
        self.conns.discard(c)

    async def _send(self, c: Conn, text: str) -> None:
        try:
            await c.ws.send_text(text)
            self.frames_sent += 1
        except Exception:  # noqa: BLE001 - a closed socket is removed by its own handler
            self.conns.discard(c)
        finally:
            c.busy = False

    async def _run(self) -> None:
        q = self.hub.subscribe()
        loop = asyncio.get_running_loop()
        try:
            while True:
                first = await q.get()
                latest = {first["approachId"]: first}
                deadline = loop.time() + TICK_S
                while (left := deadline - loop.time()) > 0:
                    with contextlib.suppress(TimeoutError):
                        m = await asyncio.wait_for(q.get(), timeout=left)
                        latest[m["approachId"]] = m
                        while not q.empty():  # drain what is already waiting without re-arming timers
                            m = q.get_nowait()
                            latest[m["approachId"]] = m
                self._snapshot.clear()
                states = list(latest.values())
                frames: dict[frozenset[str] | None, str | None] = {}
                for c in list(self.conns):
                    if c.key not in frames:
                        mine = states if c.key is None else [s for s in states if s["junctionId"] in c.key]
                        frames[c.key] = (
                            json.dumps({"type": "states", "states": mine}, separators=(",", ":"))
                            if mine
                            else None
                        )
                    text = frames[c.key]
                    if text is None:
                        continue
                    if c.busy:
                        c.skipped += 1
                        self.frames_skipped += 1
                        continue
                    c.busy = True
                    loop.create_task(self._send(c, text))
        finally:
            self.hub.unsubscribe(q)

    def status(self) -> dict:
        return {
            "clients": len(self.conns),
            "framesSent": self.frames_sent,
            "framesSkipped": self.frames_skipped,
            "tickS": TICK_S,
        }
