"""Data connectors (Admin): list configured feeds and their health, edit a tenant's mapping, and
preview how pasted sample records would be mapped. Nothing here can reach or command a signal:
preview is a pure function over the sample you paste, and mappings only change how we READ.
"""

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from ..audit_log import record
from ..auth import admin
from ..config import settings
from ..connectors.source import KINDS, load_config, make_mapping, validate_mapping
from ..connectors.spat import decode
from ..db import connect, db_available
from ..tables import connector_mappings

router = APIRouter(tags=["connectors"])
log = logging.getLogger("haribatti.connectors")


def saved_mappings() -> dict[str, dict]:
    """Mappings saved from the dashboard, keyed by connector id ({} when Postgres is down)."""
    if not db_available():
        return {}
    try:
        with connect() as c:
            return {r.connector_id: r.mapping for r in c.execute(select(connector_mappings))}
    except Exception as e:  # noqa: BLE001 - table missing before `alembic upgrade head`
        log.warning("connector mappings not readable: %s", e)
        return {}


def _connectors(request: Request) -> dict:
    return getattr(request.app.state, "connectors", {})


@router.get("/connectors")
def list_connectors(request: Request, _user: dict = Depends(admin)) -> dict:
    """Configured connectors (no URLs or secrets), their health, and which feed is live now."""
    live = _connectors(request)
    rows = []
    for cfg in load_config():
        conn = live.get(cfg["id"])
        running = cfg["id"] == settings().signal_source
        health = (
            conn.health()
            if conn and running
            else {"warnings": ["not running (not the live source; set SIGNAL_SOURCE to switch)"]}
        )
        rows.append({"id": cfg["id"], "kind": cfg["kind"], "tenant": cfg["mapping"].get("tenant"), "source": cfg["mapping"].get("source", "ITMS"),
                     "mappedApproaches": len(cfg["mapping"].get("ids") or {}), "running": running, "health": health})  # fmt: skip
    return {"active": settings().signal_source, "kinds": [*KINDS, "spat"], "connectors": rows, "readOnly": True,
            "note": "Connectors only read. HariBatti never sends anything to a signal controller."}  # fmt: skip


@router.get("/connectors/{connector_id}/mapping")
def get_mapping(connector_id: str, _user: dict = Depends(admin)) -> dict:
    saved = saved_mappings().get(connector_id)
    if saved is not None:
        return {"id": connector_id, "mapping": saved, "from": "dashboard"}
    cfg = next((c for c in load_config() if c["id"] == connector_id), None)
    if cfg is None:
        raise HTTPException(404, f"No connector '{connector_id}' in config/connectors.yaml")
    return {"id": connector_id, "mapping": cfg["mapping"], "from": "config file"}


class MappingBody(BaseModel):
    tenant: str
    source: Literal["ITMS", "CROWD", "SIM"] = "ITMS"
    fields: dict[str, str]
    ids: dict[str, str]
    colour_values: dict[str, str] = Field(default_factory=dict)
    confidence: float = 0.95


@router.patch("/connectors/{connector_id}/mapping")
def save_mapping(connector_id: str, body: MappingBody, request: Request, user: dict = Depends(admin)) -> dict:
    """Save a tenant mapping (validated against the junction registry) and apply it to the running connector."""
    cfg = next((c for c in load_config() if c["id"] == connector_id), None)
    if cfg is None:
        raise HTTPException(404, f"No connector '{connector_id}' in config/connectors.yaml")
    m = body.model_dump()
    if errs := validate_mapping(m, cfg["kind"]):
        raise HTTPException(422, {"errors": errs})
    if not db_available():
        raise HTTPException(503, "Database not running (make infra) — the mapping cannot be saved")
    with connect() as c:
        stmt = insert(connector_mappings).values(
            connector_id=connector_id, tenant=m["tenant"], mapping=m, updated_by=user["email"]
        )
        c.execute(
            stmt.on_conflict_do_update(
                index_elements=["connector_id"],
                set_={"tenant": m["tenant"], "mapping": m, "updated_by": user["email"]},
            )
        )
    if conn := _connectors(request).get(connector_id):
        conn.mapping = make_mapping(m)
    record(
        "connector_mapping",
        user["email"],
        user["role"],
        {"connector": connector_id, "approaches": len(m["ids"])},
    )
    return {"id": connector_id, "mapping": m, "from": "dashboard"}


class PreviewBody(BaseModel):
    mapping: dict[str, Any]
    sample: Any = Field(description="A list of vendor records, one record, or a SPaT JSON message")
    format: Literal["records", "spat"] = "records"
    kind: str | None = None  # the connector kind, so the same source-label rules apply as when saving


@router.post("/connectors/preview")
def preview(body: PreviewBody, _user: dict = Depends(admin)) -> dict:
    """Map pasted sample records with a draft mapping. Pure: nothing is fetched, stored or sent."""
    m = dict(body.mapping)
    if body.format == "spat":
        m["fields"] = {
            "junction": "junction",
            "approach": "approach",
            "colour": "colour",
            "remaining": "remaining",
            "timestamp": "timestamp",
        }
    errs = validate_mapping(m, body.kind)
    if errs:
        return {"errors": errs, "mapped": [], "rejected": []}
    mapping = make_mapping(m)
    raw = body.sample if isinstance(body.sample, list) else [body.sample]
    if body.format == "spat":
        raw = [r for msg in raw if isinstance(msg, dict) for r in decode(msg)]
    raw = raw[:500]
    mapped, rejected = [], []
    for r in raw:
        ps = mapping.apply(r)
        (mapped if ps else rejected).append(ps or r)
    return {
        "errors": [],
        "mapped": mapped,
        "rejected": rejected[:50],
        "counts": {"mapped": len(mapped), "rejected": len(rejected)},
    }
