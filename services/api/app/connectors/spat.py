"""SAE J2735 SPaT (Signal Phase and Timing) in its JSON form -> flat vendor records -> PhaseState.

A SPaT message lists intersections; each has signal groups with an eventState and a timing block.
Times are "TimeMark": tenths of a second within the current UTC hour (0..35999; 36001 = unknown).
We only DECODE SPaT; we never build or send one.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from .base import Mapping, ReadOnlyConnector

UNKNOWN_MARK = 36001
# J2735 MovementPhaseState (text or number) -> our colour; "dark"/"unavailable" -> None (skipped)
EVENT_STATE = {
    "unavailable": None, "dark": None,
    "stop-then-proceed": "RED", "stop-and-remain": "RED", "pre-movement": "RED",
    "permissive-movement-allowed": "GREEN", "protected-movement-allowed": "GREEN",
    "permissive-clearance": "AMBER", "protected-clearance": "AMBER",
    "caution-conflicting-traffic": "FLASHING_AMBER",
    0: None, 1: None, 2: "RED", 3: "RED", 4: "RED", 5: "GREEN", 6: "GREEN", 7: "AMBER", 8: "AMBER", 9: "FLASHING_AMBER",
}  # fmt: skip

SPAT_FIELDS = {
    "junction": "junction",
    "approach": "approach",
    "colour": "colour",
    "remaining": "remaining",
    "timestamp": "timestamp",
}


def event_colour(state: Any) -> str | None:
    key = state.lower() if isinstance(state, str) else state
    return EVENT_STATE.get(key)


def mark_seconds(end_mark: int, now: datetime) -> float | None:
    """Seconds from now until a TimeMark, wrapping at the top of the hour; None when unknown."""
    if end_mark is None or not 0 <= int(end_mark) <= 35999:
        return None
    now_mark = (now.minute * 60 + now.second) * 10 + now.microsecond // 100_000
    return ((int(end_mark) - now_mark) % 36000) / 10


def decode(msg: dict, now: datetime | None = None) -> list[dict]:
    """One SPaT JSON message -> flat records {junction, approach, colour, remaining, timestamp}."""
    now = now or datetime.now(UTC)
    out: list[dict] = []
    for ix in msg.get("intersections") or []:
        if not isinstance(ix, dict):
            continue
        iid = ix.get("id")
        iid = iid.get("id") if isinstance(iid, dict) else iid
        for st in ix.get("states") or []:
            if not isinstance(st, dict):
                continue
            events = st.get("state-time-speed") or st.get("stateTimeSpeed") or []
            if not isinstance(events, list) or not events or not isinstance(events[0], dict):
                continue
            ev = events[0]  # the current movement event
            colour = event_colour(ev.get("eventState"))
            timing = ev.get("timing") or {}
            remaining = mark_seconds(timing.get("minEndTime", UNKNOWN_MARK), now)
            if colour is None or remaining is None:
                continue
            out.append({"junction": iid, "approach": st.get("signalGroup"), "colour": colour.lower(), "remaining": remaining,
                        "timestamp": now.isoformat()})  # fmt: skip
    return out


class SpatConnector(ReadOnlyConnector):
    """Wraps any transport (HTTP, WebSocket, MQTT, replay) whose messages are SPaT JSON."""

    kind = "spat"

    def __init__(self, connector_id: str, mapping: Mapping, transport: ReadOnlyConnector):
        mapping.fields = dict(SPAT_FIELDS)
        super().__init__(connector_id, mapping)
        self.transport = transport

    async def _read(self) -> AsyncIterator[Any]:
        async for raw in self.transport._read():
            for m in raw if isinstance(raw, list) else [raw]:
                yield decode(m) if isinstance(m, dict) else []
