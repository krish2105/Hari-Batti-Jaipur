"""Data connectors (P8 W12): read-only adapters that turn a police ITMS or vendor feed into PhaseState.

base.py          ReadOnlyConnector (connect / stream / history / health) and the per-tenant Mapping
http_poll.py     HTTP JSON polling (GET only)
ws_push.py       WebSocket push (receive only)
mqtt_sub.py      MQTT subscribe (subscribe only; never publishes)
file_drop.py     CSV / Excel exports dropped in a watched folder (or pulled from SFTP into it)
spat.py          SAE J2735 SPaT messages in their JSON form
timing_import.py timing plans from CSV / Excel / PDF tables -> a PROPOSED signal_timings.csv for review
replay.py        record a feed to JSON lines and replay it (tests, demos)
source.py        ConnectorSource: plugs any connector into the API's LiveHub
There is deliberately no way to send anything to a signal: no write, publish, post or control method
exists, and tests/test_connectors.py fails if one is ever added.
"""
