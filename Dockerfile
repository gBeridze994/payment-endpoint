# syntax=docker/dockerfile:1

# --- Build stage: install the app and its dependencies into a virtual environment.
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9.27 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first, so this layer is cached until uv.lock changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable


# --- Runtime stage: only the virtual environment and the migrations.
FROM python:3.14-slim

RUN useradd --system --create-home --uid 1000 app

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY pyproject.toml alembic.ini ./
COPY migrations ./migrations

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER app
EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--access-logfile", "-", "shop.wsgi:app"]
