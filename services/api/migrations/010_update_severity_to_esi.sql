-- Migration: Update severity column to use ESI-1 through ESI-5 values
-- This migration handles existing databases with old values (CRITICAL, HIGH, etc.)
-- For fresh databases, migration 009 already uses ESI values.

-- Drop old constraint (if exists)
ALTER TABLE triage_incidents DROP CONSTRAINT IF EXISTS ck_incidents_severity;

-- Update existing values to new format (safe to run even if already ESI format)
UPDATE triage_incidents SET severity = 'ESI-1' WHERE severity = 'CRITICAL';
UPDATE triage_incidents SET severity = 'ESI-3' WHERE severity = 'HIGH';
UPDATE triage_incidents SET severity = 'ESI-4' WHERE severity = 'MEDIUM';
UPDATE triage_incidents SET severity = 'ESI-5' WHERE severity = 'LOW';
UPDATE triage_incidents SET severity = 'UNASSIGNED' WHERE severity = 'RESOLVED';

-- Add constraint with ESI values
ALTER TABLE triage_incidents ADD CONSTRAINT ck_incidents_severity
    CHECK (severity IN ('UNASSIGNED', 'ESI-1', 'ESI-2', 'ESI-3', 'ESI-4', 'ESI-5'));
