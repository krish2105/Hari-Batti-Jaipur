"""The connector contract and the per-tenant mapping from a vendor's fields and IDs to HariBatti's.

Every connector only READS: connect() opens a read connection, stream() yields PhaseState dicts,
history() returns past states it kept, health() reports freshness and clock drift. Nothing else.
"""

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

PhaseState = dict  # camelCase JSON, same shape as packages/core PhaseState

COLOURS = ("RED", "AMBER", "GREEN", "FLASHING_AMBER")
# common vendor spellings -> our colours (tenants can add their own in Mapping.colour_values)
DEFAULT_COLOURS = {
    "red": "RED", "r": "RED", "stop": "RED", "0": "RED",
    "amber": "AMBER", "yellow": "AMBER", "y": "AMBER", "a": "AMBER", "1": "AMBER",
    "green": "GREEN", "g": "GREEN", "go": "GREEN", "2": "GREEN",
    "flashing": "FLASHING_AMBER", "flashing_amber": "FLASHING_AMBER", "flash": "FLASHING_AMBER",
}  # fmt: skip
DRIFT_WARN_S = 2.0  # clock difference between the feed and this server that triggers a warning


def pick(record: dict, path: str) -> Any:
    """Read "a.b.c" (dot path) from a nested dict; None when missing."""
    cur: Any = record
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


@dataclass
class Mapping:
    """How one tenant's feed maps onto HariBatti.

    fields:  our field -> the vendor's key (dot paths allowed): junction, approach, colour, remaining, timestamp
    ids:     "<vendor junction>/<vendor approach>" -> our approach id (e.g. "SIG-114/2" -> "J05-mansarover-metro")
    source:  "ITMS" for a police feed, "CROWD" for app-derived estimates
    """

    tenant: str
    ids: dict[str, str]
    fields: dict[str, str] = field(
        default_factory=lambda: {
            "junction": "junction",
            "approach": "approach",
            "colour": "colour",
            "remaining": "remaining",
            "timestamp": "timestamp",
        }
    )
    colour_values: dict[str, str] = field(default_factory=dict)
    source: str = "ITMS"
    confidence: float = 0.95

    def colour(self, raw: Any) -> str | None:
        key = str(raw).strip().lower()
        return (
            self.colour_values.get(key)
            or DEFAULT_COLOURS.get(key)
            or (key.upper() if key.upper() in COLOURS else None)
        )

    def apply(self, record: Any) -> PhaseState | None:
        """One vendor record -> PhaseState, or None when it cannot be mapped (never raises)."""
        try:
            if not isinstance(record, dict):
                return None
            vj, va = pick(record, self.fields["junction"]), pick(record, self.fields["approach"])
            approach = self.ids.get(f"{vj}/{va}")
            colour = self.colour(pick(record, self.fields["colour"]))
            remaining = float(pick(record, self.fields["remaining"]))
            if approach is None or colour is None or not (0 <= remaining < 3600):
                return None
            ts = parse_ts(pick(record, self.fields.get("timestamp", "timestamp")))
            return {
                "junctionId": approach.split("-", 1)[0],
                "approachId": approach,
                "colour": colour,
                "secondsRemaining": round(remaining, 1),
                "confidence": self.confidence,
                "source": self.source,
                "updatedAt": (ts or datetime.now(UTC)).isoformat(),
                "feedTimestamp": ts.isoformat() if ts else None,
            }
        except (TypeError, ValueError, KeyError, AttributeError):
            return None


def parse_ts(v: Any) -> datetime | None:
    """ISO 8601 text or epoch seconds/milliseconds -> aware datetime; None when absent or unreadable."""
    if v is None or v == "":
        return None
    try:
        if isinstance(v, int | float) or (isinstance(v, str) and v.replace(".", "", 1).isdigit()):
            x = float(v)
            return datetime.fromtimestamp(x / 1000 if x > 1e11 else x, UTC)
        d = datetime.fromisoformat(str(v))
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    except (ValueError, OverflowError, OSError):
        return None


class ReadOnlyConnector:
    """Base class: subclasses implement _read() (an async iterator of raw vendor records)."""

    kind = "base"

    def __init__(self, connector_id: str, mapping: Mapping):
        self.id = connector_id
        self.mapping = mapping
        self.received = 0
        self.rejected = 0
        self.last_at: float | None = None
        self.max_drift_s = 0.0
        self.recent: list[PhaseState] = []

    async def connect(self) -> None:
        """Open the read connection (subclasses override when they need to)."""

    def _read(self) -> AsyncIterator[Any]:
        raise NotImplementedError

    async def stream(self) -> AsyncIterator[PhaseState]:
        """Mapped PhaseStates; unmappable or malformed records are counted and skipped."""
        await self.connect()
        async for raw in self._read():
            for rec in raw if isinstance(raw, list) else [raw]:
                ps = self.mapping.apply(rec)
                if ps is None:
                    self.rejected += 1
                    continue
                self.received += 1
                self.last_at = time.time()
                if ps.get("feedTimestamp"):
                    drift = abs(
                        datetime.now(UTC).timestamp()
                        - datetime.fromisoformat(ps["feedTimestamp"]).timestamp()
                    )
                    self.max_drift_s = max(self.max_drift_s * 0.95, drift)
                self.recent = (self.recent + [ps])[-500:]
                yield ps

    async def history(self, junction_id: str, start: datetime, end: datetime) -> list[PhaseState]:
        """States this connector has seen recently (the API's phase_events table keeps the long history)."""
        return [
            p
            for p in self.recent
            if p["junctionId"] == junction_id and start.isoformat() <= p["updatedAt"] <= end.isoformat()
        ]

    def health(self) -> dict:
        age = None if self.last_at is None else round(time.time() - self.last_at, 1)
        warnings = []
        if age is None or age > 10:
            warnings.append("no data in the last 10 s")
        if self.max_drift_s > DRIFT_WARN_S:
            warnings.append(
                f"feed clock differs from ours by {self.max_drift_s:.1f} s (check NTP on both sides)"
            )
        return {"id": self.id, "kind": self.kind, "tenant": self.mapping.tenant, "source": self.mapping.source, "received": self.received,
                "rejected": self.rejected, "lastDataAgeS": age, "clockDriftS": round(self.max_drift_s, 1), "warnings": warnings, "readOnly": True}  # fmt: skip
