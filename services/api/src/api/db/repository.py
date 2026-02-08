"""Repository classes for triage data access."""

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.engine import Engine

from datetime import timedelta

from services.api.src.api.db.models import (
    triage_incidents,
    triage_messages,
    triage_assessments,
    triage_audit_events,
    verified_ips,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class IncidentRepository:
    """Data access for triage incidents."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def create(self, domain: str, mode: str = "B") -> dict:
        now = _now()
        row = {
            "id": _new_id(),
            "domain": domain,
            "status": "OPEN",
            "mode": mode,
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as conn:
            conn.execute(triage_incidents.insert().values(row))
        return row

    def get(self, incident_id: str) -> dict | None:
        with self.engine.connect() as conn:
            result = conn.execute(
                select(triage_incidents).where(triage_incidents.c.id == incident_id)
            )
            row = result.mappings().first()
            return dict(row) if row else None

    def update_status(self, incident_id: str, status: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                update(triage_incidents)
                .where(triage_incidents.c.id == incident_id)
                .values(status=status, updated_at=_now())
            )

    def list_by_domain(self, domain: str, limit: int = 50) -> list[dict]:
        with self.engine.connect() as conn:
            result = conn.execute(
                select(triage_incidents)
                .where(triage_incidents.c.domain == domain)
                .order_by(triage_incidents.c.created_at.desc())
                .limit(limit)
            )
            return [dict(row) for row in result.mappings()]


class MessageRepository:
    """Data access for triage messages."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def create(self, incident_id: str, role: str, content_text: str) -> dict:
        row = {
            "id": _new_id(),
            "incident_id": incident_id,
            "role": role,
            "content_text": content_text,
            "created_at": _now(),
        }
        with self.engine.begin() as conn:
            conn.execute(triage_messages.insert().values(row))
        return row

    def list_by_incident(self, incident_id: str) -> list[dict]:
        with self.engine.connect() as conn:
            result = conn.execute(
                select(triage_messages)
                .where(triage_messages.c.incident_id == incident_id)
                .order_by(triage_messages.c.created_at.asc())
            )
            return [dict(row) for row in result.mappings()]


class AssessmentRepository:
    """Data access for triage assessments."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def create(self, incident_id: str, domain: str, result_json: dict) -> dict:
        row = {
            "id": _new_id(),
            "incident_id": incident_id,
            "domain": domain,
            "result_json": json.dumps(result_json),
            "created_at": _now(),
        }
        with self.engine.begin() as conn:
            conn.execute(triage_assessments.insert().values(row))
        return row

    def get_latest(self, incident_id: str) -> dict | None:
        with self.engine.connect() as conn:
            result = conn.execute(
                select(triage_assessments)
                .where(triage_assessments.c.incident_id == incident_id)
                .order_by(triage_assessments.c.created_at.desc())
                .limit(1)
            )
            row = result.mappings().first()
            if row:
                d = dict(row)
                d["result_json"] = json.loads(d["result_json"])
                return d
            return None


class AuditEventRepository:
    """Append-only audit event ledger."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def append(
        self,
        incident_id: str,
        trace_id: str,
        step: str,
        payload_json: dict | None = None,
        latency_ms: int | None = None,
        model_used: str | None = None,
        token_usage_json: dict | None = None,
    ) -> dict:
        row = {
            "id": _new_id(),
            "incident_id": incident_id,
            "trace_id": trace_id,
            "step": step,
            "payload_json": json.dumps(payload_json or {}),
            "latency_ms": latency_ms,
            "model_used": model_used,
            "token_usage_json": json.dumps(token_usage_json) if token_usage_json else None,
            "created_at": _now(),
        }
        with self.engine.begin() as conn:
            conn.execute(triage_audit_events.insert().values(row))
        return row

    def list_by_incident(self, incident_id: str) -> list[dict]:
        with self.engine.connect() as conn:
            result = conn.execute(
                select(triage_audit_events)
                .where(triage_audit_events.c.incident_id == incident_id)
                .order_by(triage_audit_events.c.created_at.asc())
            )
            rows = []
            for row in result.mappings():
                d = dict(row)
                d["payload_json"] = json.loads(d["payload_json"])
                if d["token_usage_json"]:
                    d["token_usage_json"] = json.loads(d["token_usage_json"])
                rows.append(d)
            return rows


class VerifiedIPRepository:
    """Cache for verified reCAPTCHA IPs (7 day TTL)."""

    VERIFICATION_DAYS = 7

    def __init__(self, engine: Engine):
        self.engine = engine
        self._table_ensured = False

    def _ensure_table(self) -> None:
        """Create verified_ips table if it doesn't exist."""
        if self._table_ensured:
            return
        from sqlalchemy import text

        # Use dialect-appropriate SQL
        is_sqlite = self.engine.dialect.name == "sqlite"
        if is_sqlite:
            create_sql = """
                CREATE TABLE IF NOT EXISTS verified_ips (
                    ip TEXT PRIMARY KEY,
                    verified_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TEXT NOT NULL
                )
            """
        else:
            create_sql = """
                CREATE TABLE IF NOT EXISTS verified_ips (
                    ip TEXT PRIMARY KEY,
                    verified_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """

        with self.engine.begin() as conn:
            conn.execute(text(create_sql))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_verified_ips_expires ON verified_ips(expires_at)
            """))
        self._table_ensured = True

    def is_verified(self, ip: str) -> bool:
        """Check if IP is verified and not expired."""
        self._ensure_table()
        now = _now()
        with self.engine.connect() as conn:
            result = conn.execute(
                select(verified_ips).where(
                    verified_ips.c.ip == ip,
                    verified_ips.c.expires_at > now,
                )
            )
            row = result.first()
            return row is not None

    def add(self, ip: str) -> None:
        """Add or update verified IP with 7 day expiry."""
        self._ensure_table()
        now = _now()
        expires = now + timedelta(days=self.VERIFICATION_DAYS)
        with self.engine.begin() as conn:
            # Upsert: delete old entry if exists, then insert
            conn.execute(verified_ips.delete().where(verified_ips.c.ip == ip))
            conn.execute(verified_ips.insert().values(
                ip=ip,
                verified_at=now,
                expires_at=expires,
            ))

    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count deleted."""
        self._ensure_table()
        now = _now()
        with self.engine.begin() as conn:
            result = conn.execute(
                verified_ips.delete().where(verified_ips.c.expires_at <= now)
            )
            return result.rowcount
