-- Verified IPs table - cache reCAPTCHA verification for 7 days
CREATE TABLE IF NOT EXISTS verified_ips (
    ip TEXT PRIMARY KEY,
    verified_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_verified_ips_expires ON verified_ips(expires_at);
