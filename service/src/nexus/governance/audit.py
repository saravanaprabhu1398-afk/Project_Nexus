"""Append-only audit sink (NX-022, SC-14, SC-20).

Invariant: an unauditable tool call must not happen. A failed audit write
aborts the operation it describes rather than letting it proceed unrecorded.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from nexus.domain.models import new_id


class AuditAction(StrEnum):
    TOOL_INVOKE = "tool.invoke"
    POLICY_DECIDE = "policy.decide"
    DATA_ACCESS = "data.access"
    MODEL_CALL = "model.call"
    EXPORT = "export"


@dataclass(frozen=True, slots=True)
class AuditRecord:
    action: AuditAction
    subject_id: str
    tenant_id: str
    resource: str
    purpose: str
    result_status: str
    id: str = field(default_factory=new_id)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    investigation_id: str | None = None
    policy_id: str | None = None
    decision: str | None = None
    reason: str | None = None
    redaction_applied: bool = False
    request_hash: str | None = None


class AuditWriteFailed(RuntimeError):
    """Raised when a record cannot be persisted. Callers must not proceed."""


class AuditSink(ABC):
    @abstractmethod
    async def record(self, entry: AuditRecord) -> None: ...


class InMemoryAuditSink(AuditSink):
    """Development and test sink. Append-only by construction: no delete method."""

    def __init__(self) -> None:
        self._entries: list[AuditRecord] = []

    async def record(self, entry: AuditRecord) -> None:
        self._entries.append(entry)

    def entries(self) -> tuple[AuditRecord, ...]:
        """Read-only view. There is deliberately no mutation accessor."""
        return tuple(self._entries)


class DatabaseAuditSink(AuditSink):
    """Writes to the append-only audit_record table (NX-022).

    On PostgreSQL the application role holds SELECT and INSERT on that table and
    nothing else, so a record cannot be altered or removed once written. A write
    failure propagates: the gateway turns it into AuditWriteFailed and the tool
    call is not treated as successful.
    """

    async def record(self, entry: AuditRecord) -> None:
        from nexus.db.models import AuditRow
        from nexus.db.repository import AuditRepository
        from nexus.db.session import get_session

        row = AuditRow(
            id=entry.id,
            tenant_id=entry.tenant_id,
            investigation_id=entry.investigation_id,
            subject_id=entry.subject_id,
            occurred_at=entry.occurred_at,
            action=str(entry.action),
            resource=entry.resource,
            purpose=entry.purpose,
            policy_id=entry.policy_id,
            decision=entry.decision,
            reason=entry.reason,
            result_status=entry.result_status,
            request_hash=entry.request_hash,
        )
        async with get_session() as session:
            await AuditRepository(session).append(row, tenant_id=entry.tenant_id)
