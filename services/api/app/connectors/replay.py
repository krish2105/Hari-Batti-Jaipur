"""Record a feed to JSON lines and replay it later (demos, contract tests, clock-drift tests).

Each line is {"t": seconds since the first message, "msg": <raw vendor message>}.
Record:  uv run python -m app.connectors.replay record <connectors.yaml id> out.jsonl --seconds 600
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .base import Mapping, ReadOnlyConnector


class ReplayConnector(ReadOnlyConnector):
    kind = "replay"

    def __init__(
        self,
        connector_id: str,
        mapping: Mapping,
        path: str | Path,
        speed: float = 1.0,
        loop: bool = False,
        retime: bool = False,
    ):
        super().__init__(connector_id, mapping)
        self.path, self.speed, self.loop = Path(path), speed, loop
        # True: stamp each record with "now" so a demo replay looks live (tests keep the recorded times)
        self.retime = retime

    def _stamp(self, msg: Any) -> Any:
        key = self.mapping.fields.get("timestamp", "")
        if not self.retime or not key or "." in key:
            return msg
        now = datetime.now(UTC).isoformat()
        if isinstance(msg, list):
            return [{**r, key: now} if isinstance(r, dict) else r for r in msg]
        return {**msg, key: now} if isinstance(msg, dict) else msg

    async def _read(self) -> AsyncIterator[Any]:
        while True:
            last_t = 0.0
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    self.rejected += 1
                    continue
                if self.speed > 0:
                    await asyncio.sleep(max(0.0, (row.get("t", last_t) - last_t) / self.speed))
                last_t = row.get("t", last_t)
                yield self._stamp(row.get("msg"))
            if not self.loop:
                return


async def record(connector: ReadOnlyConnector, out: Path, seconds: float) -> int:
    """Write the connector's raw messages (before mapping) to a JSON-lines file for `seconds`."""
    t0, n = time.monotonic(), 0
    with out.open("w", encoding="utf-8") as f:
        async for raw in connector._read():
            f.write(json.dumps({"t": round(time.monotonic() - t0, 2), "msg": raw}, default=str) + "\n")
            n += 1
            if time.monotonic() - t0 > seconds:
                break
    return n


def main() -> None:
    import argparse

    from .source import load_connectors

    ap = argparse.ArgumentParser(description="Record a configured connector's raw feed to JSON lines.")
    ap.add_argument("cmd", choices=["record"])
    ap.add_argument("connector_id")
    ap.add_argument("out", type=Path)
    ap.add_argument("--seconds", type=float, default=600)
    a = ap.parse_args()
    conn = load_connectors()[a.connector_id]
    n = asyncio.run(record(conn, a.out, a.seconds))
    print(f"[replay] wrote {n} messages to {a.out} (keep it out of git if it holds real feed data)")


if __name__ == "__main__":
    main()
