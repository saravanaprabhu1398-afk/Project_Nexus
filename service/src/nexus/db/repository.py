"""Tenant-scoped repository (ADR-10, NX-021).

There is deliberately no un-tenanted query method on this class. Every read and
every write takes a tenant_id, and the filter is applied inside the repository
rather than by the caller remembering to add it.

Retrofitting tenancy after data exists is a migration, not a change - which is
why this exists in the first commit rather than in Phase 4.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from nexus.db.models import AuditRow, EvidenceRow, Investigation, TraceStep
from nexus.domain.models import InvestigationStatus


class TenantMismatch(RuntimeError):
    """A row was about to be written under a tenant other than the caller's."""


def _assert_tenant(row_tenant: str, caller_tenant: str) -> None:
    if row_tenant != caller_tenant:
        raise TenantMismatch(
            f"row tenant {row_tenant!r} does not match caller tenant {caller_tenant!r}"
        )


class InvestigationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, investigation: Investigation, *, tenant_id: str, retention_days: int
    ) -> Investigation:
        _assert_tenant(investigation.tenant_id, tenant_id)
        investigation.expires_at = datetime.now(UTC) + timedelta(days=retention_days)
        self._session.add(investigation)
        await self._session.commit()
        return investigation

    async def get(self, *, tenant_id: str, investigation_id: str) -> Investigation | None:
        stmt = select(Investigation).where(
            Investigation.tenant_id == tenant_id,
            Investigation.id == investigation_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_subject(
        self, *, tenant_id: str, subject_id: str, limit: int = 50
    ) -> list[Investigation]:
        stmt = (
            select(Investigation)
            .where(Investigation.tenant_id == tenant_id, Investigation.subject_id == subject_id)
            .order_by(Investigation.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def set_status(
        self,
        *,
        tenant_id: str,
        investigation_id: str,
        status: InvestigationStatus,
        consumed: dict[str, int] | None = None,
        failure_code: str | None = None,
        outcome: dict[str, Any] | None = None,
    ) -> None:
        row = await self.get(tenant_id=tenant_id, investigation_id=investigation_id)
        if row is None:
            return
        row.status = str(status)
        if consumed is not None:
            row.consumed = consumed
        if failure_code is not None:
            row.failure_code = failure_code
        if outcome is not None:
            row.outcome = outcome
        if status in {
            InvestigationStatus.COMPLETE,
            InvestigationStatus.FAILED,
            InvestigationStatus.ABORTED,
        }:
            row.completed_at = datetime.now(UTC)
        await self._session.commit()


class EvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many(self, rows: list[EvidenceRow], *, tenant_id: str) -> None:
        for row in rows:
            _assert_tenant(row.tenant_id, tenant_id)
        self._session.add_all(rows)
        await self._session.commit()

    async def list_for_investigation(
        self, *, tenant_id: str, investigation_id: str
    ) -> list[EvidenceRow]:
        stmt = select(EvidenceRow).where(
            EvidenceRow.tenant_id == tenant_id,
            EvidenceRow.investigation_id == investigation_id,
        )
        return list((await self._session.execute(stmt)).scalars())


class TraceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, step: TraceStep, *, tenant_id: str) -> None:
        _assert_tenant(step.tenant_id, tenant_id)
        self._session.add(step)
        await self._session.commit()

    async def list_for_investigation(
        self, *, tenant_id: str, investigation_id: str
    ) -> list[TraceStep]:
        stmt = (
            select(TraceStep)
            .where(
                TraceStep.tenant_id == tenant_id,
                TraceStep.investigation_id == investigation_id,
            )
            .order_by(TraceStep.seq)
        )
        return list((await self._session.execute(stmt)).scalars())


class AuditRepository:
    """Append and read only. There is no update or delete method, by design."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, row: AuditRow, *, tenant_id: str) -> None:
        _assert_tenant(row.tenant_id, tenant_id)
        self._session.add(row)
        await self._session.commit()

    async def list_for_investigation(
        self, *, tenant_id: str, investigation_id: str
    ) -> list[AuditRow]:
        stmt = (
            select(AuditRow)
            .where(
                AuditRow.tenant_id == tenant_id,
                AuditRow.investigation_id == investigation_id,
            )
            .order_by(AuditRow.occurred_at)
        )
        return list((await self._session.execute(stmt)).scalars())


class RetentionPurge:
    """The delete path that ships with the store (ADR-11, NX-061).

    Audit records are intentionally absent from this class: their removal is a
    separate privileged process, not part of routine purging.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def purge_expired(  # noqa: D102 - tenant-wide by design; see class docstring
        self, *, now: datetime | None = None
    ) -> dict[str, int]:
        cutoff = now or datetime.now(UTC)
        counts: dict[str, int] = {}
        for name, model in (
            ("evidence", EvidenceRow),
            ("trace_step", TraceStep),
            ("investigation", Investigation),
        ):
            stmt = delete(model).where(model.expires_at.is_not(None), model.expires_at <= cutoff)
            result = await self._session.execute(stmt)
            counts[name] = cast("CursorResult[Any]", result).rowcount or 0
        await self._session.commit()
        return counts
