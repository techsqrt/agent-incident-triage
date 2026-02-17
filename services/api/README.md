# Triage API

FastAPI backend for the agent incident triage platform. Handles incident lifecycle, multi-domain triage assessment, voice/chat pipelines, and audit logging.

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

## Source Layout

```
src/api/
  adapters/    # External service integrations (OpenAI LLM, STT, TTS)
  core/        # Pipeline orchestration, feature flags, redaction
  db/          # SQLAlchemy engine, models, migrations, repositories
  domains/     # Pluggable domain modules (medical, sre, crypto)
  routes/      # FastAPI endpoint definitions
  schemas/     # Shared enums and Pydantic request/response models
  config.py    # Pydantic settings (env vars)
  main.py      # App factory and startup
```

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/triage/incidents` | Create incident |
| GET | `/api/triage/incidents` | List/filter incidents |
| GET | `/api/triage/incidents/{id}` | Get incident detail |
| PATCH | `/api/triage/incidents/{id}/status` | Update status |
| POST | `/api/triage/incidents/{id}/messages` | Send chat message |
| POST | `/api/triage/incidents/{id}/voice` | Voice pipeline |
| GET | `/api/triage/incidents/{id}/timeline` | Audit trail |
| GET | `/api/triage/domains` | List active domains |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///local.db` | Database connection string |
| `OPENAI_API_KEY` | — | Enables LLM extraction and TTS/STT |
| `ACTIVE_DOMAINS` | `medical` | Comma-separated list of enabled domains |
| `RECAPTCHA_SECRET_KEY` | — | Optional reCAPTCHA server key |
