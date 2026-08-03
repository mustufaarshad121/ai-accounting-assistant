# syntax=docker/dockerfile:1
FROM python:3.13-slim

# Install uv (fast Python package manager) from its official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (better layer caching), without the project itself.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy application source and Alembic config.
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

# Sync again to install the project into the environment.
RUN uv sync --frozen --no-dev

EXPOSE 8000

# Scaffold phase: run the API only. Migrations are wired in a later branch and
# must not create tables automatically at startup.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
