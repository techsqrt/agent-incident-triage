-- Core incidents table
CREATE TABLE IF NOT EXISTS triage_incidents (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL CHECK (domain IN ('medical', 'sre', 'crypto')),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'TRIAGE_READY', 'ESCALATED', 'CLOSED')),
    mode TEXT NOT NULL DEFAULT 'B' CHECK (mode IN ('A', 'B')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_incidents_domain ON triage_incidents(domain);
CREATE INDEX IF NOT EXISTS ix_incidents_status ON triage_incidents(status);
CREATE INDEX IF NOT EXISTS ix_incidents_created ON triage_incidents(created_at);
