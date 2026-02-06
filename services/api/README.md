# Triage API

FastAPI backend for the agent incident triage platform.

## Setup

```bash
cd services/api
poetry install
```

## Run

```bash
poetry run uvicorn services.api.src.api.main:app --reload
```

## Test

```bash
poetry run pytest
```
