# Install dependencies into a venv; the runtime stage copies only that result.
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBUG=false
ENV PATH="/app/.venv/bin:$PATH"

RUN groupadd --system backend \
    && useradd --system --gid backend --home-dir /app --no-create-home backend \
    && mkdir /app \
    && chown -R backend /app

WORKDIR /app

COPY --from=builder --chown=backend:backend /app/.venv /app/.venv
COPY --chown=backend:backend . .

USER backend

EXPOSE 8000
CMD ["granian", "mainsite.wsgi:application", "--interface", "wsgi", "--host", "0.0.0.0"]
