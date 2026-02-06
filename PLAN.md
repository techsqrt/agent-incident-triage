# Agent Incident Triage — Implementation Plan

## Status: ALL MILESTONES COMPLETE

### What's done
- **M1** (commit `47b604b`): Monorepo scaffold — apps/web (Next.js 15), services/api (FastAPI/Poetry), infra/docker-compose.yml, root scripts, CI workflow, domain framework with feature flags, redaction middleware, frontend domain tabs, API client + types, 12 tests passing
- **M2** (commit `8289937`): DB migrations (5 SQL files), SQLAlchemy models, repository layer (Incident/Message/Assessment/AuditEvent repos), 18 tests passing
- **M3** (commit `c49571f`): Medical Pydantic schemas, ESI-like deterministic triage rules, red-flag detection, LLM prompts, 43 new tests (61 total)
- **M4** (commit `c332ee3`): REST endpoints (create/get incident, send message, timeline), keyword-based extraction, 16 endpoint tests (77 total)
- **M5** (commits `70640a6`, `cd07254`): OpenAI adapters (STT/LLM/TTS), pipeline runner with audit logging, voice endpoint, 8 new tests (85 total)
- **M6** (commits `7d836cc`, `d8abbf3`): Start incident flow, ChatPanel, VoiceRecorder, Timeline, AssessmentCard, incident detail page with tabs
- **M7**: README, docs, final verification

---

## M3: Medical schemas + deterministic rules + unit tests (2-3 commits)

**Scope:** Pydantic schemas for medical extraction, deterministic ESI-like triage rules, red-flag detection

**Files to create:**
- `services/api/src/api/domains/medical/schemas.py` — Pydantic models: MedicalExtraction (chief_complaint, vitals, symptoms, pain_scale, medical_history, allergies, medications)
- `services/api/src/api/domains/medical/rules.py` — Deterministic triage rules: ESI acuity levels 1-5, red-flag detection (chest pain + SOB, altered mental status, severe hemorrhage, etc.), escalation logic
- `services/api/src/api/domains/medical/prompts.py` — System prompts for LLM extraction and follow-up question generation
- `services/api/tests/domain/test_medical_schemas.py` — Schema validation tests
- `services/api/tests/domain/test_medical_rules.py` — Triage rules unit tests (red flags, acuity scoring)

**Done criteria:** Rules correctly classify ESI 1-5, red flags trigger escalation, all tests pass

---

## M4: Core API endpoints + timeline (2-3 commits)

**Scope:** REST endpoints for incident CRUD, messaging, timeline

**Files to create/modify:**
- `services/api/src/api/schemas/responses.py` — Pydantic response models for API
- `services/api/src/api/routes/triage.py` — Extend with:
  - `POST /api/triage/incidents` body `{ domain, mode }` → create incident
  - `GET /api/triage/incidents/{id}` → get incident
  - `POST /api/triage/incidents/{id}/messages` body `{ content }` → send text message, run medical extract+rules, return assistant response
  - `GET /api/triage/incidents/{id}/timeline` → list audit events
- `services/api/tests/routes/__init__.py`
- `services/api/tests/routes/test_triage.py` — API endpoint tests using FastAPI TestClient

**Done criteria:** All endpoints return correct responses, tests pass, inactive domains return 400/501

---

## M5: AI adapters + medical pipeline + voice endpoint (3-4 commits)

**Scope:** OpenAI integration, voice pipeline, audit logging

**Files to create:**
- `services/api/src/api/adapters/openai_stt.py` — STT adapter (audio → text) using `gpt-4o-mini-transcribe`
- `services/api/src/api/adapters/openai_llm.py` — LLM adapter for schema-driven extraction using `gpt-4o-mini`
- `services/api/src/api/adapters/openai_tts.py` — TTS adapter (text → audio) using `gpt-4o-mini-tts`
- `services/api/src/api/core/pipeline.py` — Pipeline runner: orchestrates STT→Extract→Rules→Generate→TTS, logs each step to audit_events with trace_id, latency_ms, redacted payloads
- `services/api/src/api/routes/triage.py` — Add `POST /api/triage/incidents/{id}/voice` endpoint (accepts audio FormData, returns transcript + response_text + audio_base64 + assessment)
- `services/api/tests/core/test_pipeline.py` — Pipeline tests with mocked adapters

**Key design decisions:**
- Each adapter is a plain function (not class) for simplicity, matching baseline style
- Pipeline runner takes adapter functions as arguments for testability
- Audit events are appended per step with `trace_id` grouping them
- Redaction applied to all payloads before DB storage
- If `OPENAI_API_KEY` is empty, adapters return mock/stub responses (graceful degradation)

**Done criteria:** Voice pipeline works end-to-end (with mocks in tests), audit trail recorded

---

## M6: Frontend triage page + chat + voice + timeline UI (3-4 commits)

**Scope:** Full medical triage UX

**Files to create/modify:**
- `apps/web/src/app/triage/page.tsx` — Extend: start incident button, switch to incident view
- `apps/web/src/app/triage/[id]/page.tsx` — Incident detail page with tabs: Chat / Voice / Timeline
- `apps/web/src/app/components/ChatPanel.tsx` — Text chat: message list + input, calls POST /messages
- `apps/web/src/app/components/VoiceRecorder.tsx` — MediaRecorder → blob → POST /voice → playback audio response
- `apps/web/src/app/components/Timeline.tsx` — Fetch /timeline, render audit events with step labels, latency, pretty-printed payload JSON
- `apps/web/src/app/components/AssessmentCard.tsx` — Display current assessment (acuity, escalation status, symptoms)
- `apps/web/src/lib/api.ts` — Already has all needed functions

**UI patterns (matching baseline):**
- All `'use client'` components
- Inline styles (no CSS framework)
- `useEffect` + `useState` for data fetching
- Error/loading states

**Done criteria:** Can start incident, send text messages, record/playback voice, see timeline

---

## M7: Polish + docs + CI verification (1-2 commits)

**Scope:** Final cleanup

**Files to create/modify:**
- `README.md` — Project overview, setup instructions, architecture diagram
- `.env.example` — Verify all vars documented
- `services/api/README.md` — API endpoint documentation
- CI verification — ensure `./test.sh` passes in clean environment

**Done criteria:** README is complete, CI green, repo runs with `./run.sh`

---

## Key Conventions (from baseline audit)

- **Python:** snake_case functions, PascalCase classes, SCREAMING_SNAKE constants, `@dataclass(frozen=True)` for domain models
- **TypeScript:** camelCase functions, PascalCase components/interfaces, inline styles
- **Migrations:** raw SQL files in `services/api/migrations/`, numbered `00N_*.sql`
- **Imports:** stdlib → third-party → local (`from services.api.src.api.xxx`)
- **API patterns:** FastAPI router + `Depends()` for engine injection
- **Tests:** pytest with `pyproject.toml` config, vitest for frontend
- **Commits:** `feat:`, `fix:`, `test:`, `refactor:`, `chore:` tags, NO co-author line, small scope
- **No CSS frameworks** — inline `style={{}}` objects
- **Client-side data fetching** — `useEffect` + `useState` pattern
