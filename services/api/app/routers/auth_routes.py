"""Sign-in routes: request a one-time code, verify it, read the current user."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth import current_user, request_code, verify_code

router = APIRouter(prefix="/auth", tags=["auth"])


class Email(BaseModel):
    email: str = Field(max_length=200)


class Verify(Email):
    code: str = Field(min_length=6, max_length=6)


@router.post("/otp/request")
def otp_request(body: Email) -> dict:
    return request_code(body.email)


@router.post("/otp/verify")
def otp_verify(body: Verify) -> dict:
    return verify_code(body.email, body.code)


@router.get("/me")
def me(user: dict = Depends(current_user)) -> dict:
    return user
