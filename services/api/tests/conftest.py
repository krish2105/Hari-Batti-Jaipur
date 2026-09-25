"""Shared fixtures. Tests that need Postgres skip when `make infra` is not running."""

import pytest
from fastapi.testclient import TestClient

from app.db import db_available
from app.main import app

needs_db = pytest.mark.skipif(not db_available(), reason="Postgres not running (make infra)")


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def token(client):
    """A signed-in Operator (dev OTP flow)."""
    from app.auth import make_token

    return make_token("operator@test.local", "Operator")
