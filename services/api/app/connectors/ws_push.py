"""WebSocket push: the vendor sends JSON messages; we only receive (nothing is ever sent back)."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import websockets

from .base import Mapping, ReadOnlyConnector

log = logging.getLogger("haribatti.connectors.ws")


class WebSocketConnector(ReadOnlyConnector):
    kind = "websocket"

    def __init__(self, connector_id: str, mapping: Mapping, url: str, headers: dict[str, str] | None = None):
        super().__init__(connector_id, mapping)
        self.url, self.headers = url, headers or {}

    async def _read(self) -> AsyncIterator[Any]:
        backoff = 1.0
        while True:
            try:
                async with websockets.connect(
                    self.url, additional_headers=self.headers, open_timeout=10
                ) as ws:
                    backoff = 1.0
                    async for raw in ws:  # receive only
                        try:
                            yield json.loads(raw)
                        except ValueError:
                            self.rejected += 1
            except (OSError, websockets.WebSocketException) as e:
                log.warning("%s: WebSocket %s dropped (%s); retry in %.0fs", self.id, self.url, e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
