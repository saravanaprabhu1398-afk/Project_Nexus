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
