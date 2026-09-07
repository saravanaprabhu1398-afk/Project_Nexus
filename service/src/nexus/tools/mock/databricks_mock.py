"""Mock connector for local development (NX-018).

Shape-compatible with the Phase 2 Databricks toolset so the full agent loop is
exercisable before any external access is granted. Returns normalized Evidence,
never a provider-native object (ADR-04).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from nexus.domain.evidence import Evidence
from nexus.domain.models import Freshness, Integrity, Sensitivity, Subject
from nexus.governance.pdp import RiskClass
from nexus.tools.contract import ToolCall, ToolContract, ToolResult

_BASE = datetime(2026, 9, 7, 3, 5, tzinfo=UTC)


async def _get_run(subject: Subject, call: ToolCall) -> ToolResult:
    run_id = call.arguments.get("run_id", "run-1842")
    ev = Evidence(
        source_system="databricks",
        source_resource_id=f"{call.resource.uri}/runs/{run_id}",
        evidence_type="run_status",
        collected_at=datetime.now(UTC),
        event_at=_BASE,
        content_summary=(
            f"Run {run_id} FAILED at 03:05 UTC. Task 2 of 3 (transform_customers) "
            "terminated with an internal error. Previous run at 02:05 UTC SUCCEEDED."
        ),
        citation_key="EV-01",
        freshness=Freshness.LIVE,
        sensitivity=Sensitivity.INTERNAL,
        integrity=Integrity.VALIDATED,
        authz_context={"subject": subject.user_id, "permission": "jobs:read"},
    )
    return ToolResult(evidence=[ev])


async def _get_task_output(subject: Subject, call: ToolCall) -> ToolResult:
    ev = Evidence(
        source_system="databricks",
        source_resource_id=f"{call.resource.uri}/tasks/transform_customers",
        evidence_type="task_error",
        collected_at=datetime.now(UTC),
        event_at=_BASE + timedelta(seconds=12),
        content_summary=(
            "AnalysisException: cannot resolve 'customer_type' due to data type "
            "mismatch: expected STRING, found STRUCT<code:STRING,label:STRING>."
        ),
        citation_key="EV-02",
        freshness=Freshness.LIVE,
        sensitivity=Sensitivity.CONFIDENTIAL,
        integrity=Integrity.VALIDATED,
        authz_context={"subject": subject.user_id, "permission": "jobs:read"},
        redaction_applied=["pattern:none_matched"],
    )
    return ToolResult(evidence=[ev])


async def _compare_runs(subject: Subject, call: ToolCall) -> ToolResult:
    ev = Evidence(
        source_system="databricks",
        source_resource_id=f"{call.resource.uri}/compare",
        evidence_type="run_diff",
        collected_at=datetime.now(UTC),
        content_summary=(
            "No change in job configuration, cluster spec, or libraries between the "
            "last successful run (02:05 UTC) and the first failed run (03:05 UTC). "
            "Input row count increased 4%."
        ),
        citation_key="EV-03",
        freshness=Freshness.LIVE,
        sensitivity=Sensitivity.INTERNAL,
        integrity=Integrity.VALIDATED,
        authz_context={"subject": subject.user_id, "permission": "jobs:read"},
    )
    return ToolResult(evidence=[ev])


MOCK_TOOLS: tuple[ToolContract, ...] = (
    ToolContract(
        name="mock.databricks.get_run",
        purpose="Retrieve the status and task breakdown of a job run.",
        risk_class=RiskClass.READ,
        required_permission="jobs:read",
        input_schema={"type": "object", "properties": {"run_id": {"type": "string"}}},
        fn=_get_run,
    ),
    ToolContract(
        name="mock.databricks.get_task_output",
        purpose="Retrieve the failure message and available output of a failed task.",
        risk_class=RiskClass.READ,
        required_permission="jobs:read",
        input_schema={
            "type": "object",
            "properties": {"run_id": {"type": "string"}, "task_key": {"type": "string"}},
            "required": ["run_id"],
        },
        timeout_ms=30_000,
        fn=_get_task_output,
    ),
    ToolContract(
        name="mock.databricks.compare_runs",
        purpose="Diff a failed run against the last successful run of the same job.",
        risk_class=RiskClass.READ,
        required_permission="jobs:read",
        input_schema={
            "type": "object",
            "properties": {"failed_run_id": {"type": "string"}},
            "required": ["failed_run_id"],
        },
        fn=_compare_runs,
    ),
)
