#!/usr/bin/env bash
# Playwright webServer command: bring up the isolated compose project, load the
# WS fixtures, then stay in the foreground until Playwright sends SIGTERM.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

COMPOSE=(
  docker compose
  --project-name uitslagenportaal-e2e
  -f docker-compose.yml
  -f docker-compose.e2e.yml
)

cleanup() {
  trap - EXIT INT TERM
  "${COMPOSE[@]}" down -v --remove-orphans
}
trap cleanup EXIT INT TERM

"${COMPOSE[@]}" up -d --wait db object-storage backend frontend
"${COMPOSE[@]}" up object-storage-bootstrap
"${COMPOSE[@]}" run --rm backend-scripts python manage.py migrate
"${COMPOSE[@]}" run --rm backend-scripts python manage.py reset_and_import mainsite/tests/fixtures/eml/ws
"${COMPOSE[@]}" up -d --wait proxy

# Keep the process alive so Playwright can SIGTERM it (and run cleanup).
sleep infinity
