"""Email + one-time-code login with three roles (Viewer < Operator < Admin).

No email service is used (zero paid APIs): in development the 6-digit code is written to the API
log, and returned in the response when AUTH_DEV_ECHO_OTP=true. Codes are stored hashed, expire in
10 minutes and allow 5 attempts. Sessions are short-lived signed JWTs (HS256, JWT_SECRET).
"""

import hashlib
import hmac
import logging
import re
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import insert, select, update

from .config import settings
from .db import connect
from .tables import otp_codes, users

log = logging.getLogger("haribatti.auth")
ROLES = ("Viewer", "Operator", "Admin")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
OTP_TTL = timedelta(minutes=10)
TOKEN_TTL = timedelta(hours=12)
MAX_ATTEMPTS = 5


def _hash(email: str, code: str) -> str:
    return hmac.new(settings().jwt_secret.encode(), f"{email}:{code}".encode(), hashlib.sha256).hexdigest()


def role_for(email: str) -> str | None:
    """Existing role, Admin via ADMIN_EMAILS, Viewer on open signup, else None (not allowed)."""
    admins = {e.strip().lower() for e in settings().admin_emails.split(",") if e.strip()}
    if email in admins:
        return "Admin"
    with connect() as c:
        row = c.execute(select(users.c.role).where(users.c.email == email)).first()
    if row:
        return row.role
    return "Viewer" if settings().auth_open_signup else None


def request_code(email: str) -> dict:
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Enter a valid email address")
    if role_for(email) is None:
        raise HTTPException(403, "This email is not registered for Signal Command")
    code = f"{secrets.randbelow(1_000_000):06d}"
    with connect() as c:
        c.execute(
            update(otp_codes).where(otp_codes.c.email == email, otp_codes.c.used.is_(False)).values(used=True)
        )
        c.execute(
            insert(otp_codes).values(
                email=email, code_hash=_hash(email, code), expires_at=datetime.now(UTC) + OTP_TTL
            )
        )
    log.warning("[DEV] Signal Command login code for %s: %s (valid 10 min)", email, code)
    out = {"sent": True, "delivery": "api-log (development: no email service)"}
    if settings().auth_dev_echo_otp:
        out["devCode"] = code
    return out


def verify_code(email: str, code: str) -> dict:
    email = email.strip().lower()
    with connect() as c:
        row = c.execute(
            select(otp_codes)
            .where(otp_codes.c.email == email, otp_codes.c.used.is_(False))
            .order_by(otp_codes.c.id.desc())
            .limit(1)
        ).first()
        if row is None or row.expires_at < datetime.now(UTC) or row.attempts >= MAX_ATTEMPTS:
            raise HTTPException(401, "Code expired — request a new one")
        if not hmac.compare_digest(row.code_hash, _hash(email, code.strip())):
            c.execute(update(otp_codes).where(otp_codes.c.id == row.id).values(attempts=row.attempts + 1))
            raise HTTPException(401, "Wrong code")
        c.execute(update(otp_codes).where(otp_codes.c.id == row.id).values(used=True))
    role = role_for(email) or "Viewer"
    with connect() as c:
        if c.execute(select(users.c.id).where(users.c.email == email)).first() is None:
            c.execute(insert(users).values(email=email, role=role))
    from .audit_log import record

    record("login", email, role)
    return {"token": make_token(email, role), "email": email, "role": role}


def make_token(email: str, role: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": email, "role": role, "iat": now, "exp": now + TOKEN_TTL},
        settings().jwt_secret,
        algorithm="HS256",
    )


def current_user(request: Request) -> dict:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(401, "Sign in required")
    try:
        claims = jwt.decode(header[7:], settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise HTTPException(401, "Session expired — sign in again") from e
    return {"email": claims["sub"], "role": claims["role"]}


def require(role: str):
    """FastAPI dependency: the signed-in user must have at least this role."""

    def dep(user: dict = Depends(current_user)) -> dict:
        if ROLES.index(user["role"]) < ROLES.index(role):
            raise HTTPException(403, f"{role} role required")
        return user

    return dep


# Ready-made role checks for routes: Depends(viewer), Depends(operator), Depends(admin)
viewer = require("Viewer")
operator = require("Operator")
admin = require("Admin")
