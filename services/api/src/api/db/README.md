# db/

Database layer using SQLAlchemy Core (not ORM).

## Files

- **engine.py** — Singleton engine factory. Handles SQLite (`check_same_thread=False`) and PostgreSQL (`postgres://` -> `postgresql://` rewrite for Railway).
- **models.py** — Table definitions: `triage_incidents`, `triage_messages`, `triage_assessments`, `triage_audit_events`, `verified_ips`.
- **schemas.py** — Column-level schema constants.
- **repository.py** — Data access classes: `IncidentRepository`, `MessageRepository`, `AssessmentRepository`, `AuditEventRepository`, `RecaptchaRepository`. Each takes an engine and exposes typed CRUD methods.
- **migrate.py** — Runs raw SQL migration files from `services/api/migrations/` in order.
