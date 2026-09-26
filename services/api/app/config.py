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
    # Live feed: "sim" (default) or the id of a connector in config/connectors.yaml (P8 W12)
    signal_source: str = "sim"
    # Security (P8 W16). ENVIRONMENT=production makes the API refuse to start with development settings.
    environment: str = "development"
    trust_proxy: bool = False  # read the client IP from X-Forwarded-For (only behind our own proxy)
    otp_max_per_email_15min: int = 5
    # Alerts (P8 W11): the API log always; email and Telegram only when these are set (off by default)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    alert_email_to: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

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

    def production_problems(self) -> list[str]:
        """Settings that are fine on a laptop but unsafe on a server."""
        p = []
        if self.jwt_secret == DEV_SECRET or len(self.jwt_secret) < 32:
            p.append("JWT_SECRET must be a random secret of at least 32 characters")
        if self.auth_dev_echo_otp:
            p.append("AUTH_DEV_ECHO_OTP must be false (codes must never be returned to the browser)")
        if self.auth_open_signup:
            p.append("AUTH_OPEN_SIGNUP must be false (only invited emails may sign in)")
        if any(o.strip().startswith("http://") for o in self.cors_origins.split(",") if o.strip()):
            p.append("CORS_ORIGINS must list https:// origins only")
        if not self.admin_emails.strip():
            p.append("ADMIN_EMAILS must name at least one Admin")
        return p

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
