"""Data retention (P8 W16): delete what we promised not to keep. Runs daily inside the API and on
demand: uv run python -m app.jobs.retention

Policies (also in docs/legal/privacy-policy.md):
- sign-in codes: deleted 1 day after they expire
- audit log: kept 365 days
- study GPS traces and uploaded junction videos: 30 days (tables/folders registered by W14/W15)
"""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, inspect

from ..config import ROOT
from ..db import connect, engine
from ..tables import audit_log, metadata, otp_codes, revoked_tokens, uptime_checks

log = logging.getLogger("haribatti.retention")
DAYS = {"otp_codes": 1, "audit_log": 365, "study_traces": 30, "video_uploads": 30, "uptime_checks": 400}
UPLOAD_DIRS = [ROOT / "data/uploads/video"]  # raw uploaded videos (W15), deleted after 30 days


def run(now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    out: dict[str, int] = {}
    with connect() as c:
        out["otp_codes"] = c.execute(
            delete(otp_codes).where(otp_codes.c.expires_at < now - timedelta(days=DAYS["otp_codes"]))
        ).rowcount
        out["revoked_tokens"] = c.execute(
            delete(revoked_tokens).where(revoked_tokens.c.expires_at < now)
        ).rowcount
        out["uptime_checks"] = c.execute(
            delete(uptime_checks).where(uptime_checks.c.ts < now - timedelta(days=DAYS["uptime_checks"]))
        ).rowcount
        out["audit_log"] = c.execute(
            delete(audit_log).where(audit_log.c.ts < now - timedelta(days=DAYS["audit_log"]))
        ).rowcount
        present = set(inspect(engine()).get_table_names())
        for name in ("study_traces", "video_uploads"):
            if name in present and name in metadata.tables:
                t = metadata.tables[name]
                out[name] = c.execute(
                    delete(t).where(t.c.created_at < now - timedelta(days=DAYS[name]))
                ).rowcount
    out["video_files"] = _old_files(UPLOAD_DIRS, now - timedelta(days=DAYS["video_uploads"]))
    log.info("retention: %s", out)
    return out


def _old_files(dirs: list[Path], before: datetime) -> int:
    n = 0
    for d in dirs:
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime, UTC) < before:
                f.unlink()
                n += 1
    return n


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
