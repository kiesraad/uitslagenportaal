#!/usr/bin/env bash
set -euo pipefail

DB_NAME="uitslagen"
DB_USER="uitslagen_user"
DB_PASSWORD="password"

# Change this if needed, e.g. postgres, your Linux user, etc.
ADMIN_USER="postgres"

psql -U "$ADMIN_USER" -d postgres <<SQL
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

