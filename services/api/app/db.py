"""Database engine. The API still starts (with file-based data) when Postgres is not running."""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import Connection

from .config import settings


@lru_cache
def engine() -> Engine:
    return create_engine(
        settings().sqlalchemy_url, pool_pre_ping=True, pool_size=5, connect_args={"connect_timeout": 3}
    )


def db_available() -> bool:
    """True when Postgres answers (make infra running)."""
    try:
        with engine().connect() as c:
            c.execute(text("select 1"))
        return True
    except Exception:  # noqa: BLE001 - any connection failure means "not available"
        return False


@contextmanager
def connect() -> Iterator[Connection]:
    with engine().begin() as c:
        yield c


@contextmanager
def read_only() -> Iterator[Connection]:
    """A transaction that Postgres itself refuses to write in (used by the AI Copilot)."""
    with engine().connect() as c, c.begin():
        c.execute(text("SET TRANSACTION READ ONLY"))
        c.execute(text("SET LOCAL statement_timeout = '5s'"))
        yield c
