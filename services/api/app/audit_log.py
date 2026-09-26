"""Write audit events (sign-ins, exports, plan runs, copilot questions). Never blocks a request."""

import logging

from sqlalchemy import insert

from .db import connect
from .tables import audit_log

log = logging.getLogger("haribatti.audit")


def record(
    action: str, email: str | None = None, role: str | None = None, detail: dict | None = None
) -> None:
    try:
        with connect() as c:
            c.execute(insert(audit_log).values(action=action, email=email, role=role, detail=detail or {}))
    except Exception as e:  # noqa: BLE001 - auditing must not break the feature being audited
        log.warning("audit event not stored: %s", e)
