"""SQLAlchemy table definitions for triage platform."""

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    Float,
    String,
    Table,
    Text,
    ForeignKey,
)

metadata = MetaData()

triage_incidents = Table(
    "triage_incidents",
    metadata,
    Column("id", String, primary_key=True),
    Column("domain", String(32), nullable=False),
    Column("status", String(32), nullable=False, server_default="OPEN"),
    Column("mode", String(1), nullable=False, server_default="B"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Index("ix_incidents_domain", "domain"),
    Index("ix_incidents_status", "status"),
    Index("ix_incidents_created", "created_at"),
)

triage_messages = Table(
    "triage_messages",
    metadata,
    Column("id", String, primary_key=True),
    Column("incident_id", String, ForeignKey("triage_incidents.id"), nullable=False),
    Column("role", String(32), nullable=False),
    Column("content_text", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_messages_incident", "incident_id"),
    Index("ix_messages_created", "created_at"),
)

triage_assessments = Table(
    "triage_assessments",
    metadata,
    Column("id", String, primary_key=True),
    Column("incident_id", String, ForeignKey("triage_incidents.id"), nullable=False),
    Column("domain", String(32), nullable=False),
    Column("result_json", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_assessments_incident", "incident_id"),
)

triage_audit_events = Table(
    "triage_audit_events",
    metadata,
    Column("id", String, primary_key=True),
    Column("incident_id", String, ForeignKey("triage_incidents.id"), nullable=False),
    Column("trace_id", String, nullable=False),
    Column("step", String(64), nullable=False),
    Column("payload_json", Text, nullable=False, server_default="{}"),
    Column("latency_ms", Integer, nullable=True),
    Column("model_used", String(64), nullable=True),
    Column("token_usage_json", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_audit_incident", "incident_id"),
    Index("ix_audit_trace", "trace_id"),
    Index("ix_audit_created", "created_at"),
)

# Domain-specific metadata tables (scaffolding)

triage_sre_meta = Table(
    "triage_sre_meta",
    metadata,
    Column("id", String, primary_key=True),
    Column("incident_id", String, ForeignKey("triage_incidents.id"), nullable=False),
    Column("service", String, nullable=True),
    Column("region", String, nullable=True),
    Column("severity", String, nullable=True),
    Column("runbook_url", String, nullable=True),
    Column("alert_source", String, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_sre_meta_incident", "incident_id"),
)

triage_crypto_meta = Table(
    "triage_crypto_meta",
    metadata,
    Column("id", String, primary_key=True),
    Column("incident_id", String, ForeignKey("triage_incidents.id"), nullable=False),
    Column("symbol", String, nullable=True),
    Column("timeframe", String, nullable=True),
    Column("pct_change", Float, nullable=True),
    Column("trigger_reason", String, nullable=True),
    Column("exchange", String, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Index("ix_crypto_meta_incident", "incident_id"),
)
