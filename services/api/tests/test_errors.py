"""Unexpected server errors come back as JSON with CORS headers, so the dashboard can show the real
message instead of mistaking a 500 for "API not reachable"."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_unhandled_error_is_json_with_cors():
    origin = settings().cors_origins.split(",")[0].strip()

    @app.get("/__boom")
    def boom():
        raise RuntimeError("kaboom")

    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.get("/__boom", headers={"Origin": origin})
        assert r.status_code == 500
        assert r.headers.get("access-control-allow-origin") == origin
        assert "detail" in r.json() and "kaboom" not in r.json()["detail"]  # no internals leaked
    finally:
        app.router.routes = [rt for rt in app.router.routes if getattr(rt, "path", "") != "/__boom"]
