-- Messages exchanged during triage
CREATE TABLE IF NOT EXISTS triage_messages (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES triage_incidents(id),
    role TEXT NOT NULL CHECK (role IN ('patient', 'assistant', 'system')),
    content_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_messages_incident ON triage_messages(incident_id);
CREATE INDEX IF NOT EXISTS ix_messages_created ON triage_messages(created_at);
