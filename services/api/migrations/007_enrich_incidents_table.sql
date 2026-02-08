-- Enrich incidents table with diagnostic and history JSON fields
-- This allows full incident reproduction and explainable logs

-- Add escalation timestamp
ALTER TABLE triage_incidents ADD COLUMN IF NOT EXISTS ts_escalated TIMESTAMP WITH TIME ZONE;

-- Add diagnostic JSON for model/system metadata
-- Example: {"model_used": "gpt-4o", "model_version": "2024-01", "api_latency_ms": 450,
--           "tokens_input": 500, "tokens_output": 200, "extraction_confidence": 0.92,
--           "client_ip": "redacted", "client_ua": "Mozilla/5.0...", "feature_flags": ["voice_enabled"]}
ALTER TABLE triage_incidents ADD COLUMN IF NOT EXISTS diagnostic JSONB DEFAULT '{}';

-- Add history JSON for full interaction log
-- Example: {"interactions": [
--   {"type": "user_sent", "ts": "2024-01-15T10:30:00Z", "content": "I have a headache...", "mode": "voice", "audio_duration_ms": 3200},
--   {"type": "agent_extracted", "ts": "2024-01-15T10:30:01Z", "model": "gpt-4o", "extraction": {...}, "latency_ms": 450},
--   {"type": "agent_reasoned", "ts": "2024-01-15T10:30:01Z", "rules_applied": ["check_vitals", "check_red_flags"], "classification": {"acuity": 3}, "red_flags": []},
--   {"type": "agent_responded", "ts": "2024-01-15T10:30:02Z", "content": "I understand...", "model": "gpt-4o", "tokens": 150},
--   {"type": "agent_escalated", "ts": "2024-01-15T10:35:00Z", "reason": "chest_pain_detected", "acuity": 1},
--   {"type": "user_closed", "ts": "2024-01-15T11:00:00Z", "reason": "resolved"},
--   {"type": "user_reopened", "ts": "2024-01-15T12:00:00Z", "reason": "symptoms_returned"}
-- ]}
ALTER TABLE triage_incidents ADD COLUMN IF NOT EXISTS history JSONB DEFAULT '{"interactions": []}';

-- Update mode constraint to use readable values
-- First drop the old constraint, then add new one
-- Note: mode 'A' = voice (realtime), 'B' = chat (batch) - we'll migrate existing data
ALTER TABLE triage_incidents DROP CONSTRAINT IF EXISTS triage_incidents_mode_check;
UPDATE triage_incidents SET mode = 'voice' WHERE mode = 'A';
UPDATE triage_incidents SET mode = 'chat' WHERE mode = 'B';
ALTER TABLE triage_incidents ADD CONSTRAINT triage_incidents_mode_check CHECK (mode IN ('chat', 'voice'));

-- Add index for searching by escalation
CREATE INDEX IF NOT EXISTS ix_incidents_escalated ON triage_incidents(ts_escalated) WHERE ts_escalated IS NOT NULL;

-- Add GIN index for JSONB queries on history (for searching interactions)
CREATE INDEX IF NOT EXISTS ix_incidents_history ON triage_incidents USING GIN (history);
