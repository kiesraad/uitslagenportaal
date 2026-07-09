#!/usr/bin/env bash
set -euo pipefail

DB_NAME="uitslagen"
DB_USER="uitslagen_user"
DB_PASSWORD="password"

# On macOS with Homebrew, PostgreSQL is typically administered by your own
# macOS user account (the cluster's superuser), not "postgres".
ADMIN_USER="${ADMIN_USER:-$(whoami)}"

# Make sure psql is on PATH (Homebrew on Apple Silicon lives under /opt/homebrew).
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"

# Sanity checks
if ! command -v psql >/dev/null 2>&1; then
  echo "Error: psql not found. Install PostgreSQL with e.g.:  brew install postgresql@16" >&2
  exit 1
fi

if ! pg_isready -q; then
  echo "Error: PostgreSQL server is not running. Start it with e.g.:  brew services start postgresql@16" >&2
  exit 1
fi

psql -v ON_ERROR_STOP=1 -U "$ADMIN_USER" -d postgres <<SQL
-- Kill active connections to the DB, otherwise DROP DATABASE can fail
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${DB_NAME}'
  AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS ${DB_NAME};
DROP USER IF EXISTS ${DB_USER};

CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';

CREATE DATABASE ${DB_NAME}
  OWNER ${DB_USER}
  ENCODING 'UTF8'
  TEMPLATE template0;

GRANT CONNECT ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL

echo "Recreated database '${DB_NAME}' with owner '${DB_USER}'."