FROM python:3.13-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
COPY mitel_ommclient2/ ./mitel_ommclient2/
COPY src/ ./src/

RUN uv sync --frozen --no-dev --no-editable

# ---- runtime ----
FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

CMD ["dect-users"]
