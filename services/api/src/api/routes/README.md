# routes/

FastAPI endpoint definitions.

## Files

- **__init__.py** — Aggregates routers under the `/api/triage` prefix.
- **triage.py** — All triage endpoints: incident CRUD, chat messaging (extract -> assess -> respond), voice pipeline, timeline/audit queries, domain listing, and reCAPTCHA status. Handles status transitions (OPEN -> TRIAGE_READY -> ESCALATED/CLOSED) with validation.
