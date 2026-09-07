"""API request and response schemas (SDD 7)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from nexus.domain.models import Mode, Origin, Sensitivity


class ResourceRefIn(BaseModel):
    type: str = Field(examples=["databricks_job"])
    id: str = Field(examples=["1234"])
    workspace: str | None = None
    environment: str = "non_production"


class Constraints(BaseModel):
    max_wall_clock_ms: int | None = None
    sensitivity_ceiling: Sensitivity = Sensitivity.CONFIDENTIAL


class CreateInvestigation(BaseModel):
    intent: str = Field(default="diagnose_job_failure")
    question: str | None = None
    resource_refs: list[ResourceRefIn] = Field(min_length=1)
    constraints: Constraints = Field(default_factory=Constraints)
    origin: Origin = Origin.USER
    mode: Mode = Mode.INTERACTIVE
    correlation_id: str | None = None


class InvestigationCreated(BaseModel):
    id: str
    status: str
    correlation_id: str
    links: dict[str, str]


class EvidenceOut(BaseModel):
    id: str
    citation_key: str
    source_system: str
    source_resource_id: str
    evidence_type: str
    collected_at: datetime
    event_at: datetime | None
    freshness: str
    sensitivity: str
    integrity: str
    content_summary: str | None


class MissingEvidenceOut(BaseModel):
    what: str
    why: str
    source_system: str | None = None
    remediation: str | None = None


class InvestigationOut(BaseModel):
    id: str
    status: str
    origin: str
    mode: str
    question: str | None
    correlation_id: str
    created_at: datetime
    completed_at: datetime | None
    consumed: dict[str, int] | None
    failure_code: str | None
    #: What the evidence reports. Not a diagnosis - root-cause reasoning,
    #: confidence and the groundedness guardrail are Phase 3.
    observation_summary: str | None = None
    evidence: list[EvidenceOut] = []
    missing_evidence: list[MissingEvidenceOut] = []


class AuditEntryOut(BaseModel):
    occurred_at: datetime
    action: str
    subject_id: str
    resource: str
    purpose: str
    policy_id: str | None
    decision: str | None
    reason: str | None
    result_status: str
