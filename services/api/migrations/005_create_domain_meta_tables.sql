-- SRE domain metadata (scaffolding — inactive)
CREATE TABLE IF NOT EXISTS triage_sre_meta (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES triage_incidents(id),
    service TEXT,
    region TEXT,
    severity TEXT,
    runbook_url TEXT,
    alert_source TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sre_meta_incident ON triage_sre_meta(incident_id);

-- Crypto domain metadata (scaffolding — inactive)
CREATE TABLE IF NOT EXISTS triage_crypto_meta (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES triage_incidents(id),
    symbol TEXT,
    timeframe TEXT,
    pct_change REAL,
    trigger_reason TEXT,
    exchange TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_crypto_meta_incident ON triage_crypto_meta(incident_id);
