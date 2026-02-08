-- Clean up any incidents with invalid mode values that slipped through
-- before the frontend fix was deployed

-- Delete any incidents with invalid mode (they can't be read anyway due to constraint)
DELETE FROM triage_audit_events WHERE incident_id IN (
    SELECT id FROM triage_incidents WHERE mode NOT IN ('chat', 'voice')
);
DELETE FROM triage_messages WHERE incident_id IN (
    SELECT id FROM triage_incidents WHERE mode NOT IN ('chat', 'voice')
);
DELETE FROM triage_assessments WHERE incident_id IN (
    SELECT id FROM triage_incidents WHERE mode NOT IN ('chat', 'voice')
);
DELETE FROM triage_incidents WHERE mode NOT IN ('chat', 'voice');

-- Re-apply constraint to be safe
ALTER TABLE triage_incidents DROP CONSTRAINT IF EXISTS triage_incidents_mode_check;
ALTER TABLE triage_incidents DROP CONSTRAINT IF EXISTS ck_incidents_mode;
ALTER TABLE triage_incidents ADD CONSTRAINT ck_incidents_mode CHECK (mode IN ('chat', 'voice'));
