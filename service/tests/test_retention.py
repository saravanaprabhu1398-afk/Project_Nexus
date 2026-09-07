"""Retention (ADR-11, NX-061, doc 08).

The purge job ships with the store. A record past its retention date is
actually gone - this is the Gate 2 evidence.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from nexus.db.models import EvidenceRow, Investigation
from nexus.db.repository import EvidenceRepository, InvestigationRepository, RetentionPurge
from nexus.domain.evidence import Evidence
from nexus.domain.models import InvestigationStatus, new_id


async def test_expired_evidence_is_purged(db):
    inv = Investigation(
        id=new_id(),
        tenant_id="pilot-a",
        subject_id="eng-1",
        origin="user",
        mode="interactive",
        status=str(InvestigationStatus.COMPLETE),
        correlation_id=new_id(),
    )
    await InvestigationRepository(db).create(inv, tenant_id="pilot-a", retention_days=365)

    now = datetime.now(UTC)
    fresh = EvidenceRow(
        id=new_id(),
        tenant_id="pilot-a",
        investigation_id=inv.id,
        source_system="databricks",
        source_resource_id="ws/jobs/1234",
        evidence_type="run_status",
        collected_at=now,
        freshness="live",
        sensitivity="internal",
        integrity="validated",
        citation_key="EV-01",
        expires_at=now + timedelta(days=90),
    )
    stale = EvidenceRow(
        id=new_id(),
        tenant_id="pilot-a",
        investigation_id=inv.id,
        source_system="databricks",
        source_resource_id="ws/jobs/1234",
        evidence_type="log_excerpt",
        collected_at=now - timedelta(days=40),
        freshness="stale",
        sensitivity="confidential",
        integrity="validated",
        citation_key="EV-02",
        expires_at=now - timedelta(days=10),
    )
    await EvidenceRepository(db).add_many([fresh, stale], tenant_id="pilot-a")

    counts = await RetentionPurge(db).purge_expired()
    assert counts["evidence"] == 1

    remaining = await EvidenceRepository(db).list_for_investigation(
        tenant_id="pilot-a", investigation_id=inv.id
    )
    assert [r.id for r in remaining] == [fresh.id]


def test_evidence_gets_an_expiry_at_creation():
    """No evidence object is created without a delete path."""
    e = Evidence(
        source_system="databricks",
        source_resource_id="ws/jobs/1234/runs/1",
        evidence_type="run_status",
        collected_at=datetime.now(UTC),
        content_summary="run failed",
        citation_key="EV-01",
    )
    assert e.expires_at is None
    e.apply_retention(days=90)
    assert e.expires_at is not None
    assert not e.is_expired

    old = Evidence(
        source_system="databricks",
        source_resource_id="ws/jobs/1234/runs/1",
        evidence_type="log_excerpt",
        collected_at=datetime.now(UTC) - timedelta(days=40),
        content_summary="log line",
        citation_key="EV-02",
    )
    old.apply_retention(days=30)
    assert old.is_expired
