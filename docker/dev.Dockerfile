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

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 1) Install dependencies in a cached layer (only lock + pyproject copied)
COPY pyproject.toml uv.lock ./
COPY pyproject.toml ./
RUN uv sync --frozen --no-install-project

# 2) Copy the actual project and install it (editable is fine for dev)
COPY src ./src
COPY tests ./tests
RUN uv sync --frozen

# Copy Alembic configuration and migrations
COPY alembic.ini .
COPY alembic/ ./alembic/

# Copy and set up migration script
COPY scripts/run_migrations.sh /run_migrations.sh
RUN chmod +x /run_migrations.sh

# Copy and set up migration script
COPY scripts/run_migrations.sh /run_migrations.sh
RUN chmod +x /run_migrations.sh

# Change ownership to non-root user
RUN chown -R appuser:appuser /app /run_migrations.sh

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Set entrypoint to run migrations before starting the app
ENTRYPOINT ["/run_migrations.sh"]

CMD ["uv", "run", "uvicorn", "kavak_lite.entrypoints.http.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

