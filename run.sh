#!/bin/sh
set -e

# Auto-detect repo root from script location
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

# Parse --local flag
LOCAL_MODE=false
for arg in "$@"; do
    [ "$arg" = "--local" ] && LOCAL_MODE=true
done

# Load environment variables from .env if it exists
if [ -f "$REPO_ROOT/.env" ]; then
    set -a
    . "$REPO_ROOT/.env"
    set +a
fi
export REPO_ROOT
export PYTHONPATH="$REPO_ROOT"

cd "$REPO_ROOT"

if [ "$LOCAL_MODE" = true ]; then
    # Local mode: use docker postgres
    export DATABASE_URL="postgresql://triage:triage@localhost:5432/triage_db"

    # Detect docker compose command
    if docker compose version >/dev/null 2>&1; then
        COMPOSE="docker compose"
    elif command -v docker-compose >/dev/null 2>&1; then
        COMPOSE="docker-compose"
    else
        echo "ERROR: Neither 'docker compose' nor 'docker-compose' found."
        exit 1
    fi

    cleanup() {
        echo ""
        echo "==> Shutting down..."
        kill $API_PID $WEB_PID 2>/dev/null || true
        $COMPOSE -f "$REPO_ROOT/infra/docker-compose.yml" down
        exit 0
    }
    trap cleanup INT TERM

    echo "==> Starting Docker services (postgres, redis)"
    $COMPOSE -f "$REPO_ROOT/infra/docker-compose.yml" up -d

    echo "==> Waiting for postgres..."
    sleep 3

    # Run migrations
    echo "==> Running database migrations..."
    cd "$REPO_ROOT/services/api"
    poetry run python -m services.api.src.api.db.migrate || {
        echo "ERROR: Database migrations failed"
        exit 1
    }
    cd "$REPO_ROOT"
else
    # Remote mode: use DATABASE_URL from .env
    if [ -z "$DATABASE_URL" ]; then
        echo "ERROR: DATABASE_URL not set. Use --local for local docker postgres."
        exit 1
    fi

    cleanup() {
        echo ""
        echo "==> Shutting down..."
        kill $API_PID $WEB_PID 2>/dev/null || true
        exit 0
    }
    trap cleanup INT TERM
fi

echo "==> Using database: ${DATABASE_URL%%@*}@***"

echo "==> Starting API server"
cd "$REPO_ROOT/services/api"
poetry run uvicorn services.api.src.api.main:app --reload &
API_PID=$!
cd "$REPO_ROOT"

echo "==> Starting web app"
cd "$REPO_ROOT/apps/web"
pnpm dev &
WEB_PID=$!
cd "$REPO_ROOT"

echo ""
echo "========================================="
echo "  Services running:"
echo "    web: http://localhost:3000"
echo "    api: http://127.0.0.1:8000"
echo "========================================="
echo "  Press Ctrl+C to stop all services"
echo "========================================="
echo ""

wait
