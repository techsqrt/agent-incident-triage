# Agent Incident Triage

Modular incident triage agent pipeline with shared core and domain-specific modules.

## Architecture

```
apps/web          → Next.js 15 (App Router) frontend
services/api      → FastAPI backend with SQLAlchemy
infra/            → Docker Compose (Postgres + Redis)
```

### Domain modules

| Domain   | Status   | Description                        |
|----------|----------|------------------------------------|
| Medical  | Active   | ESI-like triage with voice support |
| SRE      | Inactive | Scaffolding only (Coming soon)     |
| Crypto   | Inactive | Scaffolding only (Coming soon)     |

### Medical triage pipeline

```
Audio → STT → Extract (LLM) → Triage Rules → Generate Response → TTS → Audio
```

- **STT**: OpenAI `gpt-4o-mini-transcribe`
- **Extraction**: Schema-driven via `gpt-4o-mini` (strict JSON output)
- **Triage rules**: Deterministic ESI acuity 1-5, red-flag detection, escalation logic
- **Response**: Follow-up question generation via `gpt-4o-mini`
- **TTS**: OpenAI `gpt-4o-mini-tts`

Every step is logged to an append-only audit ledger with trace IDs, latency, and redacted payloads.

## Quick start

```bash
# Install dependencies
./install.sh

# Copy environment variables
cp .env.example .env.local
# Edit .env.local and add your OPENAI_API_KEY

# Start everything (Postgres + Redis + API + Web)
./run.sh
```

Services:
- Web: http://localhost:3000
- API: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

## API endpoints

| Method | Path                                  | Description              |
|--------|---------------------------------------|--------------------------|
| GET    | `/health`                             | Health check             |
| GET    | `/api/triage/domains`                 | List domains and status  |
| POST   | `/api/triage/incidents`               | Create incident          |
| GET    | `/api/triage/incidents/{id}`          | Get incident             |
| POST   | `/api/triage/incidents/{id}/messages` | Send text message        |
| POST   | `/api/triage/incidents/{id}/voice`    | Voice pipeline (audio)   |
| GET    | `/api/triage/incidents/{id}/timeline` | Audit event timeline     |

## Testing

```bash
./test.sh
```

Backend: pytest (85 tests) — schemas, rules, repositories, endpoints, pipeline
Frontend: vitest (2 tests) — API client

## Environment variables

See `.env.example` for all configuration options.

| Variable               | Default                       | Description                  |
|------------------------|-------------------------------|------------------------------|
| `DATABASE_URL`         | `sqlite:///./local.db`        | Database connection string   |
| `OPENAI_API_KEY`       | (empty)                       | OpenAI API key               |
| `OPENAI_MODEL_TEXT`    | `gpt-4o-mini`                 | LLM for extraction           |
| `OPENAI_MODEL_STT`    | `gpt-4o-mini-transcribe`      | Speech-to-text model         |
| `OPENAI_MODEL_TTS`    | `gpt-4o-mini-tts`             | Text-to-speech model         |
| `ACTIVE_DOMAINS`       | `medical`                     | Comma-separated active list  |

When `OPENAI_API_KEY` is not set, all adapters return stub responses for local development.

## Project structure

```
services/api/
├── src/api/
│   ├── adapters/          # OpenAI STT/LLM/TTS adapters
│   ├── core/              # Feature flags, redaction, pipeline
│   ├── db/                # Engine, models, migrations, repositories
│   ├── domains/
│   │   ├── medical/       # Schemas, rules, prompts
│   │   ├── sre/           # Scaffolding
│   │   └── crypto/        # Scaffolding
│   ├── routes/            # FastAPI endpoints
│   └── schemas/           # Request/response models
├── migrations/            # Raw SQL migration files
└── tests/                 # pytest test suite

apps/web/
├── src/
│   ├── app/
│   │   ├── components/    # ChatPanel, VoiceRecorder, Timeline, etc.
│   │   └── triage/        # Dashboard and incident detail pages
│   └── lib/               # API client and TypeScript types
```
