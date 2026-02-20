#!/bin/bash
# Create the Flagsmith database on first PostgreSQL start.
# Mounted into /docker-entrypoint-initdb.d/ — runs only when the
# data volume is empty (i.e. first container creation).
# For existing deployments, run: CREATE DATABASE flagsmith;
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    SELECT 'CREATE DATABASE flagsmith'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'flagsmith')\gexec
    GRANT ALL PRIVILEGES ON DATABASE flagsmith TO $POSTGRES_USER;
EOSQL
