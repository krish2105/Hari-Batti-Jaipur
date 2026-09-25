"""Alembic environment: uses the API's database URL and table metadata."""

from alembic import context
from sqlalchemy import create_engine

from app.config import settings
from app.tables import metadata

target_metadata = metadata


def run_migrations_online() -> None:
    engine = create_engine(settings().sqlalchemy_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
