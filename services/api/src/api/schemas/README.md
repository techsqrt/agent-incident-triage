# schemas/

Shared Pydantic models and enums for the API layer.

## Files

- **enums.py** — `IncidentStatus` (OPEN/TRIAGE_READY/ESCALATED/CLOSED), `IncidentMode` (chat/voice), `Domain` (medical/sre/crypto), `Severity` (ESI-1 through ESI-5).
- **responses.py** — Request models (`CreateIncidentRequest`, `SendMessageRequest`, `UpdateIncidentStatusRequest`) and response models (`IncidentResponse`, `MessageResponse`, `AssessmentResponse`, `VoiceResponse`, etc.).
