FROM python:3.14-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends git tesseract-ocr tesseract-ocr-nld \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv export --locked --no-emit-project --format requirements-txt > /tmp/requirements.txt \
    && uv pip install --system -r /tmp/requirements.txt \
    && playwright install --no-progress --with-deps --only-shell chromium \
    && rm -rf /var/lib/apt/lists/*

# The ml compose service: base plus the ml group. It branches off before `COPY . .`, so editing the source does not
# rebuild it; the service mounts the repo instead. A pylock.toml keeps the wheel URLs, so torch comes from the CPU index.
FROM base AS ml
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv export --locked --no-emit-project --only-group ml --format pylock.toml > /tmp/pylock.ml.toml \
    && uv pip install --system -r /tmp/pylock.ml.toml
# A repo mounted from a Windows or macOS host has a different owner, which git refuses without this.
RUN git config --system --add safe.directory /project
ENV PYTHONPATH=/project/backend
WORKDIR /project/ml

# Last, so it stays the default target for the services that name none.
FROM base AS dev
COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
