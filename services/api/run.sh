#!/bin/bash
set -e

# Local development script for API service
# Usage:
#   ./run.sh         - Start the API server
#   ./run.sh --clear - Drop all tables, run migrations, then start

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

export DATABASE_URL="${DATABASE_URL:-postgresql://triage:triage@localhost:5432/triage_db}"
export PYTHONPATH="$PROJECT_ROOT"
export RUN_MIGRATIONS=false

cd "$SCRIPT_DIR"

if [[ "$1" == "--clear" ]]; then
    echo "Dropping all tables..."
    docker exec infra-postgres-1 psql -U triage -d triage_db -c "
        DROP SCHEMA public CASCADE;
        CREATE SCHEMA public;
        GRANT ALL ON SCHEMA public TO triage;
    "
    echo "Running migrations..."
    poetry run python -c "from services.api.src.api.db.migrate import run_migrations; run_migrations()"
fi

echo "Starting API on http://127.0.0.1:8000"
exec poetry run uvicorn services.api.src.api.main:app --reload --host 127.0.0.1 --port 8000
