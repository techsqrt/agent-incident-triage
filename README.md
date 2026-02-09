# Agent Incident Triage

A voice-powered medical triage system that listens to patients, understands their symptoms, and decides how urgent their case is — escalating to a human professional when needed.

**Live app:** https://agent-incident-triage.vercel.app

## What it does

1. A patient describes what's wrong — by voice or text
2. AI transcribes and extracts structured medical data (symptoms, pain level, vitals)
3. **Deterministic rules** (not AI) make the final call: how urgent is this? Should we escalate?
4. The system responds with a follow-up question or an immediate escalation message

The AI is an *untrusted helper* — it listens and organizes information. But the actual triage decision (urgency level, whether to escalate) is always made by [hard-coded medical rules](services/api/src/api/domains/medical/rules.py), never by the model.

## How urgency works

The system uses an ESI-like acuity scale from 1 (most urgent) to 5 (least):

| Level | Meaning | Example | Action |
|-------|---------|---------|--------|
| **1** | Immediate life threat | Heart attack, unresponsive, "I'm dying" | Escalate NOW |
| **2** | High risk | Confused, severe pain (8+), multiple red flags | Escalate NOW |
| **3** | Moderate | Single red flag, moderate pain, abnormal vitals | Continue assessment |
| **4** | Mild | Some symptoms, nothing alarming | May discharge |
| **5** | Minor | Simple complaint, no concerns | Discharge |

Levels 1-2 trigger immediate escalation to a human professional. The system stops asking follow-up questions and tells the patient help is on the way.

## What happens under the hood

```
Voice/Text → [AI] Transcribe & Extract → [Rules] Triage Decision → [AI] Respond → Voice/Text
               (untrusted helper)          (deterministic, final)     (if not escalating)
```

**The voice pipeline (5 steps):**
1. **STT** — Speech-to-text converts audio to transcript (OpenAI)
2. **Extract** — LLM pulls out structured data: chief complaint, symptoms, pain scale, vitals, mental status
3. **Triage Rules** — Deterministic rules scan for red flags and compute urgency ([see rules.py](services/api/src/api/domains/medical/rules.py))
4. **Generate** — If not escalating, LLM generates a follow-up question. If escalating, a fixed message is returned immediately
5. **TTS** — Text-to-speech converts the response back to audio

Every step is logged to an audit trail with trace IDs, latency, and redacted payloads — so you can see exactly what happened and why.

## Red flags

The rules engine scans for dangerous keywords and conditions. Some examples:

- **Cardiac:** chest pain, heart attack, cardiac arrest
- **Respiratory:** can't breathe, shortness of breath, choking
- **Neurological:** seizure, stroke, slurred speech
- **Bleeding:** severe bleeding, uncontrolled bleeding
- **Psychiatric:** suicidal, self-harm
- **Vitals:** heart rate > 150 or < 40, O2 < 90%, temp >= 104F, blood pressure < 80

Full list and logic: [rules.py](services/api/src/api/domains/medical/rules.py)

## Risk Signals (Conviction-Based Escalation)

Beyond keyword matching, the system extracts **structured risk signals** with confidence scores. Each signal has:
- A value (true/false or yes/no/unknown)
- A conviction score (0.0 to 1.0) indicating model confidence

**Critical signals extracted:**
| Signal | Threshold | Trigger |
|--------|-----------|---------|
| Suicidal ideation | 0.2 | Very low threshold — escalate even with slight suspicion |
| Self-harm intent | 0.2 | Very low threshold — safety first |
| Homicidal ideation | 0.4 | Moderate threshold |
| Cannot breathe | 0.5 | Value = "no" OR conviction >= threshold |
| Chest pain | 0.5 | Value = "yes" OR conviction >= threshold |
| Neurological deficit | 0.5 | Value = "yes" OR conviction >= threshold |
| Uncontrolled bleeding | 0.5 | Value = "yes" OR conviction >= threshold |

**How it works:**
1. LLM extracts structured data including risk signals with conviction scores
2. Deterministic rules evaluate each signal against thresholds
3. If ANY critical signal triggers, the case is escalated immediately
4. The response NEVER says "minor concern" if any risk flag is triggered

This two-layer system (keywords + conviction thresholds) ensures dangerous cases are caught even when phrased ambiguously (e.g., "I want to finish with myself").

## Quick start

```bash
./install.sh          # Install dependencies
cp .env.example .env  # Add your OPENAI_API_KEY
./run.sh --local      # Start everything with local Docker Postgres
```

- Web: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

**Options:**
- `./run.sh --local` — Uses local Docker Postgres (recommended for development)
- `./run.sh` — Uses DATABASE_URL from .env (for production/remote DB)

## Testing

```bash
./test.sh
```

## Architecture

```
apps/web/         → Next.js 15 frontend (voice recorder, chat, timeline)
services/api/     → FastAPI backend (pipeline, rules, audit trail)
infra/            → Docker Compose (Postgres)
```

Data is stored in Postgres: incidents, messages, assessments, and an append-only audit event ledger. The timeline view shows human-readable logs of each interaction step.
