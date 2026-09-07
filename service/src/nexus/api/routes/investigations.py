"""Investigation endpoints (NX-002, NX-003, NX-019, NX-127).

Asynchronous by construction (ADR-01): POST acknowledges within the 2s target
and the work runs afterwards, because a 2s acknowledgement and a 5-minute
diagnosis cannot both be met by a synchronous request.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, Request, Response, status

from nexus.api.deps import current_subject
from nexus.api.errors import ErrorCode, NexusError
from nexus.api.schemas import (
    AuditEntryOut,
    CreateInvestigation,
    EvidenceOut,
    InvestigationCreated,
    InvestigationOut,
    MissingEvidenceOut,
)
from nexus.db.models import EvidenceRow, Investigation
from nexus.db.repository import (
    AuditRepository,
    EvidenceRepository,
    InvestigationRepository,
)
from nexus.db.session import get_session
from nexus.domain.models import (
    InvestigationStatus,
    ResourceRef,
    Sensitivity,
    Subject,
    new_id,
)
from nexus.observability.logging import bind_correlation, get_logger

router = APIRouter(prefix="/v1/investigations", tags=["investigations"])

#: FastAPI resolves the authenticated subject for every route below.
CurrentSubject = Annotated[Subject, Depends(current_subject)]
log = get_logger(__name__)


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=InvestigationCreated)
async def create_investigation(
    body: CreateInvestigation,
    request: Request,
    background: BackgroundTasks,
    response: Response,
    subject: CurrentSubject,
) -> InvestigationCreated:
    settings = request.app.state.settings
    if settings.disabled:
        raise NexusError(
            ErrorCode.SERVICE_DISABLED,
            "NEXUS is disabled",
            remediation="Contact the on-call owner; the kill switch is engaged.",
        )

    correlation_id = body.correlation_id or new_id()
    investigation_id = new_id()
    bind_correlation(correlation_id, investigation_id)

    ref = body.resource_refs[0]
    resource = ResourceRef(
        system="databricks",
        resource_id=f"{ref.workspace or 'ws'}/jobs/{ref.id}",
        environment=ref.environment,
    )

    row = Investigation(
        id=investigation_id,
        tenant_id=subject.tenant_id,
        subject_id=subject.user_id,
        origin=str(body.origin),
        mode=str(body.mode),
        status=str(InvestigationStatus.QUEUED),
        question_text=body.question,
        resolved_target={"system": resource.system, "resource_id": resource.resource_id},
        prompt_version=request.app.state.prompt_version,
        policy_version=request.app.state.policy_version,
        budget={
            "wall_clock_ms": settings.budget_wall_clock_ms,
            "tool_calls": settings.budget_tool_calls,
            "plan_steps": settings.budget_plan_steps,
        },
        correlation_id=correlation_id,
    )
    async with get_session() as session:
        await InvestigationRepository(session).create(
            row,
            tenant_id=subject.tenant_id,
            retention_days=settings.retention_trace_days,
        )

    background.add_task(
        _execute,
        request.app,
        subject,
        investigation_id,
        body.intent,
        resource,
        body.constraints.sensitivity_ceiling,
    )

    response.headers["Location"] = f"/v1/investigations/{investigation_id}"
    return InvestigationCreated(
        id=investigation_id,
        status=str(InvestigationStatus.QUEUED),
        correlation_id=correlation_id,
        links={
            "self": f"/v1/investigations/{investigation_id}",
            "evidence": f"/v1/investigations/{investigation_id}/evidence",
            "audit": f"/v1/investigations/{investigation_id}/audit",
        },
    )


async def _execute(
    app: FastAPI,
    subject: Subject,
    investigation_id: str,
    intent: str,
    resource: ResourceRef,
    ceiling: Sensitivity,
) -> None:
    orchestrator = app.state.orchestrator
    async with get_session() as session:
        repo = InvestigationRepository(session)
        await repo.set_status(
            tenant_id=subject.tenant_id,
            investigation_id=investigation_id,
            status=InvestigationStatus.INVESTIGATING,
        )

    outcome = await orchestrator.run(
        subject=subject,
        investigation_id=investigation_id,
        intent=intent,
        resource=resource,
        sensitivity_ceiling=ceiling,
    )

    async with get_session() as session:
        rows = [
            EvidenceRow(
                id=e.id,
                tenant_id=subject.tenant_id,
                investigation_id=investigation_id,
                source_system=e.source_system,
                source_resource_id=e.source_resource_id,
                evidence_type=e.evidence_type,
                collected_at=e.collected_at,
                event_at=e.event_at,
                freshness=str(e.freshness),
                sensitivity=str(e.sensitivity),
                integrity=str(e.integrity),
                authz_context=e.authz_context,
                content_ref=e.content_ref,
                content_summary=e.content_summary,
                citation_key=e.citation_key,
                redaction_applied={"applied": e.redaction_applied},
                retention_class=e.retention_class,
                expires_at=e.expires_at,
            )
            for e in outcome.loop.evidence
        ]
        if rows:
            await EvidenceRepository(session).add_many(rows, tenant_id=subject.tenant_id)
        await InvestigationRepository(session).set_status(
            tenant_id=subject.tenant_id,
            investigation_id=investigation_id,
            status=outcome.status,
            consumed=outcome.consumed,
            failure_code=outcome.failure_code,
        )
    app.state.missing_evidence[investigation_id] = outcome.loop.missing
    app.state.observation_summary[investigation_id] = outcome.observation_summary


@router.get("/{investigation_id}", response_model=InvestigationOut)
async def get_investigation(
    investigation_id: str,
    request: Request,
    subject: CurrentSubject,
) -> InvestigationOut:
    async with get_session() as session:
        row = await InvestigationRepository(session).get(
            tenant_id=subject.tenant_id, investigation_id=investigation_id
        )
        if row is None:
            raise NexusError(
                ErrorCode.RESOURCE_NOT_FOUND,
                "investigation not found",
                remediation="Check the id, and that it belongs to your tenant.",
            )
        evidence = await EvidenceRepository(session).list_for_investigation(
            tenant_id=subject.tenant_id, investigation_id=investigation_id
        )

    missing = request.app.state.missing_evidence.get(investigation_id, [])
    return InvestigationOut(
        id=row.id,
        status=row.status,
        origin=row.origin,
        mode=row.mode,
        question=row.question_text,
        correlation_id=row.correlation_id,
        created_at=row.created_at,
        completed_at=row.completed_at,
        consumed=row.consumed,
        failure_code=row.failure_code,
        observation_summary=request.app.state.observation_summary.get(investigation_id),
        evidence=[_evidence_out(e) for e in evidence],
        missing_evidence=[
            MissingEvidenceOut(
                what=m.what, why=m.why, source_system=m.source_system, remediation=m.remediation
            )
            for m in missing
        ],
    )


@router.get("/{investigation_id}/evidence", response_model=list[EvidenceOut])
async def list_evidence(
    investigation_id: str,
    subject: CurrentSubject,
) -> list[EvidenceOut]:
    async with get_session() as session:
        rows = await EvidenceRepository(session).list_for_investigation(
            tenant_id=subject.tenant_id, investigation_id=investigation_id
        )
    return [_evidence_out(r) for r in rows]


@router.get("/{investigation_id}/audit", response_model=list[AuditEntryOut])
async def get_audit(
    investigation_id: str,
    subject: CurrentSubject,
) -> list[AuditEntryOut]:
    """US-08: an auditor can reconstruct the complete request, access, tool,
    policy and outcome trace for one incident.

    Read from the append-only table rather than process memory, so the trail
    survives a restart and is scoped to the caller's tenant by the repository.
    """
    async with get_session() as session:
        rows = await AuditRepository(session).list_for_investigation(
            tenant_id=subject.tenant_id, investigation_id=investigation_id
        )
    return [
        AuditEntryOut(
            occurred_at=r.occurred_at,
            action=r.action,
            subject_id=r.subject_id,
            resource=r.resource,
            purpose=r.purpose,
            policy_id=r.policy_id,
            decision=r.decision,
            reason=r.reason,
            result_status=r.result_status,
        )
        for r in rows
    ]


@router.post("/{investigation_id}/abort", status_code=status.HTTP_202_ACCEPTED)
async def abort_investigation(
    investigation_id: str,
    subject: CurrentSubject,
) -> dict[str, str]:
    async with get_session() as session:
        await InvestigationRepository(session).set_status(
            tenant_id=subject.tenant_id,
            investigation_id=investigation_id,
            status=InvestigationStatus.ABORTED,
        )
    return {"id": investigation_id, "status": str(InvestigationStatus.ABORTED)}


def _evidence_out(row: EvidenceRow) -> EvidenceOut:
    return EvidenceOut(
        id=row.id,
        citation_key=row.citation_key,
        source_system=row.source_system,
        source_resource_id=row.source_resource_id,
        evidence_type=row.evidence_type,
        collected_at=row.collected_at.replace(tzinfo=row.collected_at.tzinfo or UTC),
        event_at=row.event_at,
        freshness=row.freshness,
        sensitivity=row.sensitivity,
        integrity=row.integrity,
        content_summary=row.content_summary,
    )


_ = datetime  # re-exported for typing clarity in schemas
