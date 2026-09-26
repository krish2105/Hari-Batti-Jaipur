"""HTTP JSON polling: GET a vendor URL every few seconds and map each record. Only GET is ever sent."""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .base import Mapping, ReadOnlyConnector, pick

log = logging.getLogger("haribatti.connectors.http")


class HttpPollConnector(ReadOnlyConnector):
    kind = "http_poll"

    def __init__(self, connector_id: str, mapping: Mapping, url: str, every_s: float = 1.0, records_path: str = "",
                 headers: dict[str, str] | None = None, transport: httpx.AsyncBaseTransport | None = None):  # fmt: skip
        super().__init__(connector_id, mapping)
        self.url, self.every_s, self.records_path = url, every_s, records_path
        self.headers = headers or {}  # e.g. an API key read from .env, never hard-coded
        self._transport = transport  # tests pass an httpx.MockTransport

    async def _read(self) -> AsyncIterator[Any]:
        backoff = self.every_s
        async with httpx.AsyncClient(timeout=10, headers=self.headers, transport=self._transport) as client:
            while True:
                try:
                    r = await client.get(self.url)
                    r.raise_for_status()
                    body = r.json()
                    yield pick(body, self.records_path) if self.records_path else body
                    backoff = self.every_s
                except (httpx.HTTPError, ValueError) as e:
                    log.warning("%s: GET %s failed (%s); retry in %.0fs", self.id, self.url, e, backoff)
                    backoff = min(backoff * 2, 30)
                await asyncio.sleep(backoff)
