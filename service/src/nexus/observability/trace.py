"""Trace step persistence (NX-032).

The loop emits a record per step. Keeping this behind an interface means the
loop stays free of database concerns and remains testable with a null sink,
which is the same shape the audit sink uses.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from nexus.domain.models import new_id


@dataclass(frozen=True, slots=True)
class TraceEvent:
    investigation_id: str
    tenant_id: str
    seq: int
    step_type: str
    started_at: datetime
    ended_at: datetime
    id: str = field(default_factory=new_id)
    tool_name: str | None = None
    input_hash: str | None = None
    policy_decision_id: str | None = None
    outcome: str | None = None
    error_class: str | None = None
    latency_ms: int | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None


def hash_arguments(arguments: dict[str, Any]) -> str:
    """Fingerprint tool arguments without persisting their values.

    An auditor can prove two calls were identical without the trace holding
    whatever was passed in.
    """
    canonical = json.dumps(arguments, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def utcnow() -> datetime:
    return datetime.now(UTC)


class TraceSink(ABC):
    @abstractmethod
    async def record(self, event: TraceEvent) -> None: ...


class NullTraceSink(TraceSink):
    """Used where a trace is not wanted. Records nothing and never fails."""

    async def record(self, event: TraceEvent) -> None:
        return None


class InMemoryTraceSink(TraceSink):
    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    async def record(self, event: TraceEvent) -> None:
        self._events.append(event)

    def events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)


class DatabaseTraceSink(TraceSink):
    """Persists to trace_step, with the retention expiry the purge job reads."""

    def __init__(self, retention_days: int) -> None:
        self._retention_days = retention_days

    async def record(self, event: TraceEvent) -> None:
        from datetime import timedelta

        from nexus.db.models import TraceStep
        from nexus.db.repository import TraceRepository
        from nexus.db.session import get_session

        row = TraceStep(
            id=event.id,
            tenant_id=event.tenant_id,
            investigation_id=event.investigation_id,
            seq=event.seq,
            step_type=event.step_type,
            tool_name=event.tool_name,
            input_hash=event.input_hash,
            policy_decision_id=event.policy_decision_id,
            outcome=event.outcome,
            error_class=event.error_class,
            latency_ms=event.latency_ms,
            tokens_in=event.tokens_in,
            tokens_out=event.tokens_out,
            started_at=event.started_at,
            ended_at=event.ended_at,
            expires_at=event.started_at + timedelta(days=self._retention_days),
        )
        async with get_session() as session:
            await TraceRepository(session).append(row, tenant_id=event.tenant_id)
