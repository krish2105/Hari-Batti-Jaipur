"""Sign-in routes: request a one-time code, verify it, read the current user."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..auth import current_user, request_code, revoke, verify_code
from ..ratelimit import per_ip

router = APIRouter(prefix="/auth", tags=["auth"])


class Email(BaseModel):
    email: str = Field(max_length=200)


class Verify(Email):
    code: str = Field(min_length=6, max_length=6)


@router.post("/otp/request")
def otp_request(body: Email, request: Request) -> dict:
    per_ip(request, "otp-request", limit=20, window_s=900)  # plus 5 per email (auth.request_code)
    return request_code(body.email)


@router.post("/otp/verify")
def otp_verify(body: Verify, request: Request) -> dict:
    per_ip(request, "otp-verify", limit=30, window_s=900)  # plus 5 wrong tries per code
    return verify_code(body.email, body.code)


@router.get("/me")
def me(user: dict = Depends(current_user)) -> dict:
    return {"email": user["email"], "role": user["role"]}


@router.post("/logout")
def logout(user: dict = Depends(current_user)) -> dict:
    """End this session on the server too (the token is refused from now on)."""
    if user.get("jti") and user.get("exp"):
        revoke(user["jti"], user["exp"])
    return {"signedOut": True}
