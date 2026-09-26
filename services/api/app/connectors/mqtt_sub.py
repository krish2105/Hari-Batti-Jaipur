"""MQTT subscribe-only connector (paho-mqtt, used under its BSD-3-Clause option).

The client subscribes to a topic and never publishes: the paho client is kept private and this class
exposes no publish method (tests/test_connectors.py checks that).
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from .base import Mapping, ReadOnlyConnector

log = logging.getLogger("haribatti.connectors.mqtt")


class MqttConnector(ReadOnlyConnector):
    kind = "mqtt"

    def __init__(self, connector_id: str, mapping: Mapping, host: str, topic: str, port: int = 1883,
                 username: str | None = None, password: str | None = None):  # fmt: skip
        super().__init__(connector_id, mapping)
        self.host, self.port, self.topic = host, port, topic
        self._auth = (username, password)  # from .env; never logged
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=5000)

    def _on_message(self, loop: asyncio.AbstractEventLoop, payload: bytes) -> None:
        """Runs on paho's network thread: hand the payload to the asyncio loop."""
        try:
            msg = json.loads(payload)
        except ValueError:
            self.rejected += 1
            return
        loop.call_soon_threadsafe(self._put, msg)

    def _put(self, msg: Any) -> None:
        if self._queue.full():
            self._queue.get_nowait()
        self._queue.put_nowait(msg)

    async def _read(self) -> AsyncIterator[Any]:
        import paho.mqtt.client as mqtt  # imported here so the API starts without an MQTT broker configured

        loop = asyncio.get_running_loop()
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id=f"haribatti-{self.id}", clean_session=True
        )
        if self._auth[0]:
            client.username_pw_set(*self._auth)
        client.on_connect = lambda c, _u, _f, rc, _p: rc == 0 and c.subscribe(self.topic, qos=0)
        client.on_message = lambda _c, _u, m: self._on_message(loop, m.payload)
        client.reconnect_delay_set(1, 30)
        client.connect_async(self.host, self.port, keepalive=30)
        client.loop_start()
        try:
            while True:
                yield await self._queue.get()
        finally:
            client.loop_stop()
            client.disconnect()
