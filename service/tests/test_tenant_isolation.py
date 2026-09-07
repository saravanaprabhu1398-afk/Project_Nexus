"""Tenant isolation (ADR-10, NX-021, SC-18).

Cross-tenant tests belong in CI from the first commit, not only in the Phase 4
security suite - by Phase 4 the data model is already fixed.
"""

from __future__ import annotations

from nexus.db.models import Investigation
from nexus.db.repository import (
    AuditRepository,
    EvidenceRepository,
    InvestigationRepository,
    TenantMismatch,
    TraceRepository,
)
from nexus.domain.models import InvestigationStatus, new_id


def _investigation(tenant: str, subject: str = "eng-1") -> Investigation:
    return Investigation(
        id=new_id(),
        tenant_id=tenant,
        subject_id=subject,
        origin="user",
        mode="interactive",
        status=str(InvestigationStatus.QUEUED),
        question_text="Why did the ingestion job fail?",
        correlation_id=new_id(),
    )


async def test_investigation_is_not_readable_from_another_tenant(db):
    repo = InvestigationRepository(db)
    row = await repo.create(_investigation("pilot-a"), tenant_id="pilot-a", retention_days=365)

    assert await repo.get(tenant_id="pilot-a", investigation_id=row.id) is not None
    assert await repo.get(tenant_id="pilot-b", investigation_id=row.id) is None


async def test_listing_never_crosses_tenants(db):
    repo = InvestigationRepository(db)
    await repo.create(_investigation("pilot-a"), tenant_id="pilot-a", retention_days=365)
    await repo.create(_investigation("pilot-a"), tenant_id="pilot-a", retention_days=365)
    await repo.create(_investigation("pilot-b"), tenant_id="pilot-b", retention_days=365)

    a = await repo.list_for_subject(tenant_id="pilot-a", subject_id="eng-1")
    b = await repo.list_for_subject(tenant_id="pilot-b", subject_id="eng-1")
    assert len(a) == 2
    assert len(b) == 1
    assert {r.tenant_id for r in a} == {"pilot-a"}


async def test_status_update_cannot_reach_another_tenant(db):
    repo = InvestigationRepository(db)
    row = await repo.create(_investigation("pilot-a"), tenant_id="pilot-a", retention_days=365)

    await repo.set_status(
        tenant_id="pilot-b",
        investigation_id=row.id,
        status=InvestigationStatus.ABORTED,
    )
    still = await repo.get(tenant_id="pilot-a", investigation_id=row.id)
    assert still is not None
    assert still.status == str(InvestigationStatus.QUEUED)


async def test_writing_a_row_under_the_wrong_tenant_is_refused(db):
    """The caller states the tenant, and the row must agree with it.

    Without this, a caller that built the object with the wrong tenant_id would
    persist it silently.
    """
    import pytest

    repo = InvestigationRepository(db)
    with pytest.raises(TenantMismatch):
        await repo.create(_investigation("pilot-a"), tenant_id="pilot-b", retention_days=365)


def test_no_repository_exposes_an_untenanted_query():
    """Guards the design rule itself (ADR-10).

    Every public method on every repository must take tenant_id. If someone
    adds a convenience `get_all()`, this fails and they have to justify it.
    RetentionPurge is exempt: it is a scheduled tenant-wide job, not a query
    path reachable from a request.
    """
    import inspect

    for repo in (
        InvestigationRepository,
        EvidenceRepository,
        TraceRepository,
        AuditRepository,
    ):
        for name, member in inspect.getmembers(repo, inspect.isfunction):
            if name.startswith("_"):
                continue
            params = inspect.signature(member).parameters
            assert "tenant_id" in params, f"{repo.__name__}.{name}() has no tenant_id parameter"
