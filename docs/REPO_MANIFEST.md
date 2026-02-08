# Repository Manifest

This document codifies the conventions and rules for this repository. Follow these guidelines to maintain consistency and avoid common mistakes.

## What to Never Commit

These files and directories must NEVER be committed to git:

- `node_modules/` — Install locally, never track
- `__pycache__/` and `*.pyc` — Python bytecode
- `.pytest_cache/` — Pytest cache
- `local.db` — Local SQLite database
- `.env` and `.env.local` — Environment files with secrets
- `.next/` — Next.js build output
- `coverage/` — Test coverage reports

The root `.gitignore` is configured to ignore all of these. If git status shows any of them, do not commit.

## Local Development

All local development goes through root scripts:

```bash
./install.sh   # Install all dependencies (pnpm + poetry + playwright)
./run.sh       # Start everything (Docker + migrations + API + web)
./test.sh      # Run all tests (backend + frontend + e2e)
```

Do not run services individually unless debugging. The root scripts handle environment setup, Docker orchestration, and cleanup.

## Dependency Upgrades

- **Do not upgrade Next.js** outside of an explicit decision and review
- **Do not upgrade major versions** of any dependency without discussion
- **Lock files must be committed** (pnpm-lock.yaml, poetry.lock)

## CI Requirements

- CI must run the root `./test.sh` script
- All tests must pass before merging
- The API Docker image must build and start successfully

## Commit Message Style

Use simple tags without parentheses:

```
feat: add new feature
fix: resolve bug
chore: update dependencies
docs: improve documentation
test: add test coverage
refactor: restructure code
ci: update workflow
build: change build config
perf: improve performance
style: format code
```

## Directory Structure

```
apps/web/         → Next.js frontend
services/api/     → FastAPI backend
infra/            → Docker Compose and infrastructure
docs/             → Documentation
scripts/          → Helper scripts
```

Keep this structure. Do not add new top-level directories without discussion.
