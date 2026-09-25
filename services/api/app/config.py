"""API settings, read from the repo .env (see .env.example). Defaults are for local development only."""

import warnings
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parents[1]  # services/api
ROOT = API_DIR.parents[1]  # repo root
DEV_SECRET = "dev-only-not-a-secret-set-JWT_SECRET-in-your-env-file"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://haribatti:haribatti@localhost:5434/haribatti"
    redis_url: str = "redis://localhost:6380/0"
    redis_channel: str = "signals"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    # Auth: email + one-time code. There is no email service (zero paid APIs), so in development the
    # code is printed in the API log (and returned in the response when AUTH_DEV_ECHO_OTP=true).
    jwt_secret: str = DEV_SECRET
    auth_dev_echo_otp: bool = True
    auth_open_signup: bool = True  # unknown emails become Viewers (development)
    admin_emails: str = ""  # comma-separated emails that get the Admin role
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    @field_validator("jwt_secret")
    @classmethod
    def _secret_not_blank(cls, v: str) -> str:
        """A blank JWT_SECRET (copied from .env.example) falls back to the dev default, loudly."""
        if not v.strip():
            warnings.warn(
                "JWT_SECRET is blank — using the development default. Set it in .env.", stacklevel=2
            )
            return DEV_SECRET
        return v

    @property
    def sqlalchemy_url(self) -> str:
        """Accept plain postgresql:// URLs from .env and use the psycopg 3 driver."""
        url = self.database_url
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
        return url


@lru_cache
def settings() -> Settings:
    return Settings()
