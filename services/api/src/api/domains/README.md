# domains/

Pluggable domain modules. Each domain implements `DomainModule` (defined in `base.py`) and is registered in `registry.py` at import time.

## Architecture

- **base.py** — Abstract `DomainModule` class. Defines the interface: `domain_key`, `assess()`, `get_extraction_schema()`, `get_severity_label()`, `explain_event()`, etc.
- **registry.py** — `DomainRegistry` singleton. Maps domain keys to modules, enforces feature-flag gating via `is_domain_active()`.
- **schemas.py** — Shared Pydantic models used across domains.
- **__init__.py** — Auto-registers all domain modules on import.

## Domain Modules

### medical/
Fully implemented ESI-based medical triage. Includes deterministic symptom extraction (`extract.py`), rule-based acuity scoring (`rules.py`), and LLM prompt templates (`prompts.py`).

### sre/
Stub for infrastructure incident triage. Schema and module defined; `assess()` returns placeholder.

### crypto/
Stub for crypto/DeFi incident triage. Schema and module defined; `assess()` returns placeholder.

## Adding a New Domain

1. Create `domains/<name>/` with `module.py` and `schemas.py`
2. Implement `DomainModule` in `module.py`
3. Register in `domains/__init__.py`
4. Add the key to `feature_flags.ALL_DOMAINS`
