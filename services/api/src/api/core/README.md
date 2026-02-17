# core/

Cross-cutting business logic used by routes and adapters.

## Files

- **pipeline.py** — Voice pipeline orchestrator. Runs the full STT -> Extract -> Rules -> Generate -> TTS flow with per-step error handling, audit logging, and trace IDs. Adapter functions are injectable for testing.
- **feature_flags.py** — Domain activation control. Reads `ACTIVE_DOMAINS` setting and exposes `get_active_domains()` / `is_domain_active()`.
- **redaction.py** — Sensitive data redaction for audit logs. Hashes PII fields (SSN, phone, email) and pattern-matches sensitive strings before storage.
