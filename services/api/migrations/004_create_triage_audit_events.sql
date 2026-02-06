-- Append-only audit event ledger
CREATE TABLE IF NOT EXISTS triage_audit_events (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES triage_incidents(id),
    trace_id TEXT NOT NULL,
    step TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    latency_ms INTEGER,
    model_used TEXT,
    token_usage_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_audit_incident ON triage_audit_events(incident_id);
CREATE INDEX IF NOT EXISTS ix_audit_trace ON triage_audit_events(trace_id);
CREATE INDEX IF NOT EXISTS ix_audit_created ON triage_audit_events(created_at);
