FROM python:3.14-alpine

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables to optimize Python/uv
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_PYTHON_CACHE_DIR=/root/.cache/uv/python
ENV UV_SYSTEM_PYTHON=1
ENV UV_LINK_MODE=copy

# Disable debug mode
ENV DEBUG=false

# Add a user and let it own /app
RUN addgroup -S backend \
    && adduser -S backend -G backend \
    && mkdir /app \
    && chown -R backend /app

WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv export --locked --no-dev --no-emit-project --format requirements-txt > /tmp/requirements.txt \
    && uv pip install --system -r /tmp/requirements.txt

# Copy application code
COPY --chown=backend:backend . .

# Run as the non-root backend user
USER backend

EXPOSE 8000
CMD ["granian", "mainsite.wsgi:application", "--interface", "wsgi", "--host", "0.0.0.0"]
