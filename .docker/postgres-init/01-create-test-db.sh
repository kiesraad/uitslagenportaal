#!/bin/bash
# Runs automatically on first container init (postgres:16 entrypoint convention:
# any *.sh/*.sql in /docker-entrypoint-initdb.d/ executes against a fresh data dir).
# Only fires when db_data is empty — drop the volume to re-trigger it.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE uitslagenportaal_test OWNER $POSTGRES_USER;
EOSQL
