#!/bin/sh
set -e

# Auto-detect repo root from script location
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
export REPO_ROOT
export PYTHONPATH="$REPO_ROOT"

cd "$REPO_ROOT"

echo "==> REPO_ROOT: $REPO_ROOT"

echo "==> Running backend tests"
cd "$REPO_ROOT/services/api"
poetry run pytest
cd "$REPO_ROOT"

echo "==> Running frontend unit tests"
cd "$REPO_ROOT/apps/web"
pnpm test
cd "$REPO_ROOT"

# Skip e2e tests on CI (set CI=true to skip)
if [ "$CI" = "true" ]; then
    echo "==> Skipping e2e tests on CI"
else
    echo "==> Running frontend e2e tests"
    cd "$REPO_ROOT/apps/web"
    pnpm test:e2e
    cd "$REPO_ROOT"
fi

echo "==> All tests passed"
