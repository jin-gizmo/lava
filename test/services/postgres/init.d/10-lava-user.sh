#!/bin/bash

# Create the lava user. We do this as a shell script not an SQL as we want to use
# environment vars from the docker compose file (which come from .env).

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-!
DO
\$do\$
    BEGIN
        IF
            EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_LAVA_USER}') THEN
            RAISE NOTICE 'Role "${DB_LAVA_USER}" already exists. Skipping.';
        ELSE
            RAISE NOTICE 'Creating role "${DB_LAVA_USER}".';
            CREATE ROLE ${DB_LAVA_USER} LOGIN PASSWORD '${DB_LAVA_PASSWORD}';
        END IF;
    END
\$do\$;
!
