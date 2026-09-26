"""Usage metering per tenant (P8 W17): counts signed-in API calls per tenant, user and day.

A call belongs to the tenant in its path (/tenants/{id}/..., or the pilot's tenant for /pilots/{id});
other calls belong to the user's first tenant membership, else to the Jaipur police pilot. Counts
are kept in memory and written once a minute, so metering never slows a request.
"""

import asyncio
import contextlib
import logging
import re
from collections import Counter
from datetime import UTC, datetime

import jwt
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from . import db
from .config import settings
from .tables import pilots, tenant_members, usage_daily

log = logging.getLogger("haribatti.metering")
TENANT_PATH = re.compile(r"^/tenants/([a-z0-9-]+)")
PILOT_PATH = re.compile(r"^/pilots/(\d+)")
_counts: Counter = Counter()
_home: dict[str, str] = {}
_pilot_tenant: dict[int, str] = {}
DEFAULT_TENANT = "jaipur-police"


def caller(auth_header: str) -> str | None:
    """Email of a signed-in caller (signature checked), else None. Revocation is checked by the route."""
    if not auth_header.lower().startswith("bearer "):
        return None
    try:
        return jwt.decode(auth_header[7:], settings().jwt_secret, algorithms=["HS256"])["sub"]
    except jwt.PyJWTError:
        return None


def tenant_for(path: str, email: str) -> str:
    if m := TENANT_PATH.match(path):
        return m.group(1)
    if m := PILOT_PATH.match(path):
        pid = int(m.group(1))
        if pid not in _pilot_tenant:
            with contextlib.suppress(Exception), db.connect() as c:
                row = c.execute(select(pilots.c.tenant_id).where(pilots.c.id == pid)).first()
                _pilot_tenant[pid] = row.tenant_id if row else DEFAULT_TENANT
        return _pilot_tenant.get(pid, DEFAULT_TENANT)
    if email not in _home:
        _home[email] = DEFAULT_TENANT
        with contextlib.suppress(Exception), db.connect() as c:
            row = c.execute(
                select(tenant_members.c.tenant_id)
                .where(tenant_members.c.email == email)
                .order_by(tenant_members.c.tenant_id)
            ).first()
            if row:
                _home[email] = row.tenant_id
    return _home[email]


def count(path: str, auth_header: str) -> None:
    if path.startswith(("/health", "/ready", "/metrics", "/docs", "/openapi")):
        return
    email = caller(auth_header)
    if email:
        _counts[(datetime.now(UTC).date(), tenant_for(path, email), email)] += 1


def flush() -> int:
    """Write the counters to usage_daily (adds to today's totals)."""
    if not _counts:
        return 0
    batch = dict(_counts)
    _counts.clear()
    with db.connect() as c:
        for (day, tenant, email), n in batch.items():
            stmt = pg_insert(usage_daily).values(day=day, tenant_id=tenant, email=email, calls=n)
            c.execute(
                stmt.on_conflict_do_update(
                    index_elements=["day", "tenant_id", "email"], set_={"calls": usage_daily.c.calls + n}
                )
            )
    return len(batch)


async def run() -> None:
    while True:
        await asyncio.sleep(60)
        try:
            await asyncio.to_thread(flush)
        except Exception as e:  # noqa: BLE001 - metering must never break the API
            log.debug("usage not written: %s", e)
