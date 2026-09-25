"""HariBatti API entry point.

P1 only has a health check. P3 adds PhaseSource/SimSource, all endpoints and the database.
The API is read-only: it never sends commands to a traffic signal.
"""

from fastapi import FastAPI

app = FastAPI(
    title="HariBatti API",
    description="Read-only signal countdown + audit API for the Mansarovar corridor (J01–J08).",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Simple liveness check used by `make api` verification and later by the apps."""
    return {"status": "ok", "service": "haribatti-api"}
