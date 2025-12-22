# syntax=docker/dockerfile:1
FROM python:3.14.2-slim AS base

# Copy uv binaries from Astral's distroless image (recommended by uv docs)
# (You can pin a uv version later; start unpinned for convenience.)
COPY --from=ghcr.io/astral-sh/uv:debian /usr/local/bin/uv /usr/local/bin/uv
COPY --from=ghcr.io/astral-sh/uv:debian /usr/local/bin/uvx /usr/local/bin/uvx

WORKDIR /app

# Speed + reproducibility knobs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app/src

# 1) Install dependencies in a cached layer (only lock + pyproject copied)
COPY pyproject.toml uv.lock ./
COPY pyproject.toml ./
RUN uv sync --frozen --no-install-project

# 2) Copy the actual project and install it (editable is fine for dev)
COPY src ./src
COPY tests ./tests
RUN uv sync --frozen

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "kavak_lite.entrypoints.http.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

