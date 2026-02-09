-- Add severity classification column to incidents table
-- Allows filtering by classified severity level

-- Add severity column with default UNASSIGNED
ALTER TABLE triage_incidents ADD COLUMN IF NOT EXISTS severity VARCHAR(16) DEFAULT 'UNASSIGNED' NOT NULL;

-- Add check constraint for valid severity values
ALTER TABLE triage_incidents DROP CONSTRAINT IF EXISTS ck_incidents_severity;
ALTER TABLE triage_incidents ADD CONSTRAINT ck_incidents_severity
    CHECK (severity IN ('UNASSIGNED', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'RESOLVED'));

-- Add index for severity filtering
CREATE INDEX IF NOT EXISTS ix_incidents_severity ON triage_incidents(severity);

-- Add index for updated_at filtering (for time-based queries)
CREATE INDEX IF NOT EXISTS ix_incidents_updated ON triage_incidents(updated_at);
