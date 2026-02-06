-- Triage assessment results per incident
CREATE TABLE IF NOT EXISTS triage_assessments (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES triage_incidents(id),
    domain TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_assessments_incident ON triage_assessments(incident_id);
