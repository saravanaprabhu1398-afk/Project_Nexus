"""Persistence model (SDD 6.1, NX-020).

Every table carries tenant_id as the first column of every composite index
(ADR-10). Every table that stores retrievable content carries expires_at, so
no store is created without a delete path (ADR-11).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from nexus.domain.models import new_id


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Investigation(Base):
    __tablename__ = "investigation"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    question_text: Mapped[str | None] = mapped_column(Text)
    resolved_target: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    policy_version: Mapped[str | None] = mapped_column(String(64))
    budget: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    consumed: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    failure_code: Mapped[str | None] = mapped_column(String(48))
    #: stop_reason, observation_summary and missing_evidence. Persisted rather
    #: than held in process memory: an investigation that stopped early must
    #: still look like one after a restart, and a second replica must see the
    #: same answer.
    outcome: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_investigation_tenant_created", "tenant_id", "created_at"),
        Index("ix_investigation_tenant_subject", "tenant_id", "subject_id"),
        Index("ix_investigation_expires", "expires_at"),
    )


class EvidenceRow(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    investigation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("investigation.id"), nullable=False
    )
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    source_resource_id: Mapped[str] = mapped_column(String(512), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    freshness: Mapped[str] = mapped_column(String(16), nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(16), nullable=False)
    integrity: Mapped[str] = mapped_column(String(16), nullable=False)
    authz_context: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    content_ref: Mapped[str | None] = mapped_column(String(512))
    content_summary: Mapped[str | None] = mapped_column(Text)
    citation_key: Mapped[str] = mapped_column(String(32), nullable=False)
    redaction_applied: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    retention_class: Mapped[str] = mapped_column(String(32), nullable=False, default="evidence")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_evidence_tenant_investigation", "tenant_id", "investigation_id"),
        Index("ix_evidence_expires", "expires_at"),
    )


class TraceStep(Base):
    __tablename__ = "trace_step"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    investigation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("investigation.id"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(32), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(128))
    input_hash: Mapped[str | None] = mapped_column(String(64))
    policy_decision_id: Mapped[str | None] = mapped_column(String(36))
    outcome: Mapped[str | None] = mapped_column(String(24))
    error_class: Mapped[str | None] = mapped_column(String(48))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_trace_tenant_investigation_seq", "tenant_id", "investigation_id", "seq"),
        Index("ix_trace_expires", "expires_at"),
    )


class AuditRow(Base):
    """Append-only. The application role is granted INSERT and SELECT only;
    see migrations/README for the grant statement (NX-022)."""

    __tablename__ = "audit_record"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    investigation_id: Mapped[str | None] = mapped_column(String(36))
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    resource: Mapped[str] = mapped_column(String(512), nullable=False)
    purpose: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_id: Mapped[str | None] = mapped_column(String(128))
    decision: Mapped[str | None] = mapped_column(String(24))
    reason: Mapped[str | None] = mapped_column(Text)
    result_status: Mapped[str] = mapped_column(String(32), nullable=False)
    request_hash: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        Index("ix_audit_tenant_occurred", "tenant_id", "occurred_at"),
        Index("ix_audit_tenant_investigation", "tenant_id", "investigation_id"),
    )
