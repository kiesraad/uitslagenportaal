#!/usr/bin/env bash
set -e

# Kill any container still holding port 5679, then run the importer under
# debugpy. VS Code attaches with "Django: attach management command (Docker)".
docker ps -q --filter publish=5679 | xargs -r docker stop

docker compose run --rm -p 5679:5679 backend \
  python -Xfrozen_modules=off -m debugpy \
  --listen 0.0.0.0:5679 --wait-for-client \
  manage.py import_next_github_commits GR2026
