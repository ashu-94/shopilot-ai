#!/bin/sh
set -eu
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=ON_ERROR_STOP=1 --set=app_password="$APP_DATABASE_PASSWORD" <<'SQL'
CREATE ROLE shopilot LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'app_password';
GRANT CONNECT ON DATABASE shopilot TO shopilot;
GRANT USAGE, CREATE ON SCHEMA public TO shopilot;
SQL
