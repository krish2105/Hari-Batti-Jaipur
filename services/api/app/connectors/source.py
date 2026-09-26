"""Build connectors from config/connectors.yaml and plug one into the API's LiveHub.

SIGNAL_SOURCE=sim (default) keeps the simulator; SIGNAL_SOURCE=<connector id> switches the live feed
to that connector. Secrets (tokens, passwords) are never in the YAML: it names environment variables
(from the gitignored .env) and we read them here.
"""

import os
import re
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ..config import ROOT
from ..sources.sim import SimSource
from .base import Mapping, PhaseState, ReadOnlyConnector
from .file_drop import FileDropConnector
from .http_poll import HttpPollConnector
from .mqtt_sub import MqttConnector
from .replay import ReplayConnector
from .spat import SpatConnector
from .timing_import import known_junctions
from .ws_push import WebSocketConnector

KINDS = {"http_poll": HttpPollConnector, "websocket": WebSocketConnector, "mqtt": MqttConnector,
         "file_drop": FileDropConnector, "replay": ReplayConnector}  # fmt: skip
APPROACH_ID = re.compile(r"^J0[1-8]-[a-z0-9]+(-[a-z0-9]+)*$")
FIELD_KEYS = ("junction", "approach", "colour", "remaining")


def validate_mapping(m: dict[str, Any], kind: str | None = None) -> list[str]:
    """Problems with a mapping (empty list = fine). Junction IDs must exist in data/junction_registry.csv.
    SIM is allowed only for a replay (a recorded synthetic demo feed), so made-up data is never labelled ITMS."""
    errs: list[str] = []
    if not str(m.get("tenant") or "").strip():
        errs.append("tenant is required")
    allowed = ("ITMS", "CROWD", "SIM") if kind == "replay" else ("ITMS", "CROWD")
    if m.get("source", "ITMS") not in allowed:
        errs.append(f"source must be one of {', '.join(allowed)} for this connector")
    fields = m.get("fields") or {}
    errs += [f"fields.{k} is required" for k in FIELD_KEYS if not str(fields.get(k) or "").strip()]
    ids = m.get("ids") or {}
    if not isinstance(ids, dict) or not ids:
        errs.append("ids must map at least one '<vendor junction>/<vendor approach>' to an approach id")
        return errs
    known = known_junctions()
    for k, v in ids.items():
        if "/" not in str(k):
            errs.append(f"'{k}': vendor key must look like '<junction>/<approach>'")
        if not APPROACH_ID.match(str(v)):
            errs.append(f"'{v}': approach id must look like 'J05-mansarover-metro'")
        elif str(v)[:3] not in known:
            errs.append(f"'{v}': junction {str(v)[:3]} is not in data/junction_registry.csv")
    if not 0 < float(m.get("confidence", 0.95)) <= 1:
        errs.append("confidence must be between 0 and 1")
    return errs


def make_mapping(m: dict[str, Any]) -> Mapping:
    base = Mapping(tenant=str(m["tenant"]), ids={str(k): str(v) for k, v in m["ids"].items()})
    if m.get("fields"):
        base.fields = {**base.fields, **{k: str(v) for k, v in m["fields"].items()}}
    base.colour_values = {str(k).lower(): str(v) for k, v in (m.get("colour_values") or {}).items()}
    base.source = m.get("source", "ITMS")
    base.confidence = float(m.get("confidence", 0.95))
    return base


def _env_map(names: dict[str, str] | None) -> dict[str, str]:
    """{"Authorization": "ITMS_TOKEN"} -> {"Authorization": os.environ["ITMS_TOKEN"]} (missing ones skipped)."""
    return {h: os.environ[v] for h, v in (names or {}).items() if os.environ.get(v)}


def build(cfg: dict[str, Any]) -> ReadOnlyConnector:
    """One connector from its YAML block."""
    cid, kind = cfg["id"], cfg["kind"]
    if errs := validate_mapping(cfg["mapping"], kind if kind != "spat" else cfg["transport"].get("kind")):
        raise ValueError(f"connector '{cid}': " + "; ".join(errs))
    mapping = make_mapping(cfg["mapping"])
    if kind == "spat":
        inner = dict(cfg["transport"], id=f"{cid}-transport", mapping=cfg["mapping"])
        return SpatConnector(cid, mapping, build(inner))
    if kind == "http_poll":
        return HttpPollConnector(
            cid,
            mapping,
            cfg["url"],
            float(cfg.get("every_s", 1)),
            cfg.get("records_path", ""),
            _env_map(cfg.get("headers_env")),
        )
    if kind == "websocket":
        return WebSocketConnector(cid, mapping, cfg["url"], _env_map(cfg.get("headers_env")))
    if kind == "mqtt":
        return MqttConnector(cid, mapping, cfg["host"], cfg["topic"], int(cfg.get("port", 1883)),
                             os.environ.get(cfg.get("username_env", "")), os.environ.get(cfg.get("password_env", "")))  # fmt: skip
    if kind == "file_drop":
        return FileDropConnector(cid, mapping, ROOT / cfg["folder"], float(cfg.get("every_s", 5)))
    if kind == "replay":
        return ReplayConnector(
            cid,
            mapping,
            ROOT / cfg["path"],
            float(cfg.get("speed", 1)),
            bool(cfg.get("loop", True)),
            bool(cfg.get("retime", True)),
        )
    raise ValueError(f"unknown connector kind '{kind}' (use one of {', '.join([*KINDS, 'spat'])})")


def config_path() -> Path:
    return Path(os.environ.get("CONNECTORS_FILE") or ROOT / "config/connectors.yaml")


def load_config(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or config_path()
    if not p.exists():
        return []
    return list((yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("connectors") or [])


def load_connectors(
    path: Path | None = None, overrides: dict[str, dict] | None = None
) -> dict[str, ReadOnlyConnector]:
    """All configured connectors; a mapping saved from the dashboard (overrides) wins over the YAML one."""
    out = {}
    for cfg in load_config(path):
        if overrides and cfg["id"] in overrides:
            cfg = {**cfg, "mapping": overrides[cfg["id"]]}
        out[cfg["id"]] = build(cfg)
    return out


class ConnectorSource:
    """PhaseSource over a connector, so the LiveHub, WebSockets and phase_events work unchanged."""

    def __init__(self, connector: ReadOnlyConnector):
        self.connector = connector
        self.name = connector.mapping.source

    async def stream(self) -> AsyncIterator[PhaseState]:
        async for ps in self.connector.stream():
            yield ps

    async def history(self, junction_id: str, start: datetime, end: datetime) -> list[PhaseState]:
        return await SimSource.history(self, junction_id, start, end)  # type: ignore[arg-type]  # same phase_events table
