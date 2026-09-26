# HariBatti API image (P8 W18). Python 3.12 + uv; the API reads the public data files and model
# reports from the repo layout. Video intake (PyTorch) is not included: it runs on the operator's machine.
FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/ml/pyproject.toml services/ml/uv.lock* services/ml/
COPY services/ml/ml services/ml/ml
COPY services/api/pyproject.toml services/api/uv.lock services/api/
RUN cd services/api && uv sync --frozen --no-dev --no-install-project
COPY services/api services/api
COPY services/ml/reports services/ml/reports
COPY services/sim/reports services/sim/reports
COPY services/sim/assumptions.toml services/sim/assumptions.toml
COPY services/cv/reports services/cv/reports
COPY data data
COPY config config
RUN useradd --uid 10001 --create-home app && mkdir -p data/uploads && chown -R app data/uploads
USER app
WORKDIR /app/services/api
EXPOSE 8000
# workers: set WEB_CONCURRENCY (default 2); see docs/scaling.md
CMD ["sh", "-c", "uv run --no-sync python -m app.bootstrap && exec uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-2} --proxy-headers --forwarded-allow-ips='*' --ws-per-message-deflate false --backlog 4096 --timeout-graceful-shutdown 3"]
