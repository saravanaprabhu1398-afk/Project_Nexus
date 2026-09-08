"""Databricks toolset (NX-045..NX-052).

Each tool returns normalized Evidence, never a provider-native object - that is
the portability seam (ADR-04). No Databricks field name crosses upward out of
this module.

Serverless workspaces expose no cluster events, so cluster-startup diagnosis
(IC-04) is deliberately absent rather than silently returning nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from nexus.domain.evidence import Evidence
from nexus.domain.models import Freshness, Integrity, Sensitivity, Subject
from nexus.governance.pdp import RiskClass
from nexus.observability.logging import get_logger
from nexus.tools.contract import ToolCall, ToolContract, ToolResult
from nexus.tools.databricks.client import DatabricksClient

log = get_logger(__name__)

FAILED_STATES = {"FAILED", "TIMEDOUT", "INTERNAL_ERROR", "CANCELED"}


def _ms(value: Any) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(int(value) / 1000, tz=UTC)


def _state(run: dict[str, Any]) -> str:
    state = run.get("state") or run.get("status") or {}
    return str(
        state.get("result_state")
        or (state.get("termination_details") or {}).get("code")
        or state.get("life_cycle_state")
        or state.get("state")
        or "UNKNOWN"
    )


def _evidence(
    *,
    resource: str,
    kind: str,
    summary: str,
    citation: str,
    subject: Subject,
    event_at: datetime | None = None,
    sensitivity: Sensitivity = Sensitivity.INTERNAL,
) -> Evidence:
    return Evidence(
        source_system="databricks",
        source_resource_id=resource,
        evidence_type=kind,
        collected_at=datetime.now(UTC),
        event_at=event_at,
        content_summary=summary,
        citation_key=citation,
        freshness=Freshness.LIVE,
        sensitivity=sensitivity,
        integrity=Integrity.VALIDATED,
        authz_context={"subject": subject.user_id, "permission": "jobs:read"},
    )


def _job_id(call: ToolCall) -> str:
    explicit = call.arguments.get("job_id")
    if explicit:
        return str(explicit)
    return call.resource.resource_id.rsplit("/", 1)[-1]


def _diff(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return [
        f"{key}: {before.get(key)!r} -> {after.get(key)!r}"
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]


def build_tools(client: DatabricksClient) -> tuple[ToolContract, ...]:
    """Bind the toolset to one client. Every contract is READ."""

    async def get_run(subject: Subject, call: ToolCall) -> ToolResult:
        run_id = call.arguments.get("run_id")
        if run_id is None:
            listing = await client.jobs_get("runs/list", {"job_id": _job_id(call), "limit": 25})
            runs = listing.get("runs", [])
            if not runs:
                return ToolResult(evidence=[])
            failed = [r for r in runs if _state(r) in FAILED_STATES]
            run_id = (failed or runs)[0].get("run_id")

        run = await client.jobs_get("runs/get", {"run_id": run_id})
        tasks = run.get("tasks", [])
        failed_tasks = [t for t in tasks if _state(t) in FAILED_STATES]
        first_failed = failed_tasks[0].get("task_key") if failed_tasks else None
        summary = f"Run {run_id} finished {_state(run)}. {len(tasks)} task(s); " + (
            f"first failing task: {first_failed}."
            if first_failed
            else "no task reported a failure."
        )
        return ToolResult(
            evidence=[
                _evidence(
                    resource=f"jobs/{run.get('job_id')}/runs/{run_id}",
                    kind="run_status",
                    summary=summary,
                    citation="EV-RUN",
                    subject=subject,
                    event_at=_ms(run.get("start_time")),
                )
            ],
            raw_ref=str(run_id),
        )

    async def get_task_output(subject: Subject, call: ToolCall) -> ToolResult:
        run_id = call.arguments["run_id"]
        run = await client.jobs_get("runs/get", {"run_id": run_id})
        tasks = run.get("tasks") or [{"run_id": run_id}]
        wanted = call.arguments.get("task_key")

        evidence: list[Evidence] = []
        for index, task in enumerate(tasks, start=1):
            if wanted and task.get("task_key") != wanted:
                continue
            task_run_id = task.get("run_id", run_id)
            try:
                output = await client.jobs_get("runs/get-output", {"run_id": task_run_id})
            except Exception as exc:  # noqa: BLE001
                # A task with no retrievable output is a gap in the evidence,
                # not a failure of the investigation. Log it so the gap is
                # visible rather than silent.
                log.info(
                    "task_output_unavailable",
                    task_key=task.get("task_key"),
                    run_id=task_run_id,
                    reason=str(exc),
                )
                continue
            body = output.get("error") or output.get("logs") or ""
            trace = output.get("error_trace") or ""
            if not body and not trace:
                continue
            evidence.append(
                _evidence(
                    resource=f"jobs/{run.get('job_id')}/runs/{task_run_id}/output",
                    kind="task_error",
                    summary=f"{task.get('task_key', 'task')}: {body}\n{trace}".strip(),
                    citation=f"EV-ERR-{index}",
                    subject=subject,
                    event_at=_ms(task.get("start_time")),
                    # Task output carries log content - the least governed and
                    # highest-risk evidence source (doc 08).
                    sensitivity=Sensitivity.CONFIDENTIAL,
                )
            )
        return ToolResult(evidence=evidence)

    async def compare_runs(subject: Subject, call: ToolCall) -> ToolResult:
        """Deterministic diff of the last success against the first failure.

        Code does this, not the model (ADR-05).
        """
        job_id = _job_id(call)
        listing = await client.jobs_get("runs/list", {"job_id": job_id, "limit": 50})
        runs = listing.get("runs", [])
        failed = next((r for r in runs if _state(r) in FAILED_STATES), None)
        succeeded = next((r for r in runs if _state(r) == "SUCCESS"), None)
        if not failed or not succeeded:
            return ToolResult(evidence=[])

        detail_f = await client.jobs_get("runs/get", {"run_id": failed["run_id"]})
        detail_s = await client.jobs_get("runs/get", {"run_id": succeeded["run_id"]})
        changes = _diff(
            detail_s.get("job_parameters") or detail_s.get("overriding_parameters") or {},
            detail_f.get("job_parameters") or detail_f.get("overriding_parameters") or {},
        )
        secs_s = (detail_s.get("execution_duration") or 0) / 1000
        secs_f = (detail_f.get("execution_duration") or 0) / 1000
        summary = (
            f"Last success run {succeeded['run_id']} vs first failure run "
            f"{failed['run_id']}. "
            + ("Parameter changes: " + "; ".join(changes) if changes else "No parameter changes.")
            + f" Duration {secs_s:.0f}s -> {secs_f:.0f}s."
        )
        return ToolResult(
            evidence=[
                _evidence(
                    resource=f"jobs/{job_id}/compare",
                    kind="run_diff",
                    summary=summary,
                    citation="EV-DIFF",
                    subject=subject,
                )
            ]
        )

    async def get_job_config(subject: Subject, call: ToolCall) -> ToolResult:
        job_id = _job_id(call)
        job = await client.jobs_get("get", {"job_id": job_id})
        settings = job.get("settings", {})
        tasks = settings.get("tasks", [])
        schedule = (settings.get("schedule") or {}).get("quartz_cron_expression", "none")
        summary = (
            f"Job '{settings.get('name', job_id)}' has {len(tasks)} task(s): "
            + ", ".join(t.get("task_key", "?") for t in tasks)
            + f". Schedule: {schedule}."
        )
        return ToolResult(
            evidence=[
                _evidence(
                    resource=f"jobs/{job_id}",
                    kind="job_config",
                    summary=summary,
                    citation="EV-CFG",
                    subject=subject,
                )
            ]
        )

    async def get_schema(subject: Subject, call: ToolCall) -> ToolResult:
        full_name = call.arguments["table"]
        table = await client.get(f"/api/2.1/unity-catalog/tables/{full_name}")
        columns = table.get("columns", [])
        summary = f"{full_name} has {len(columns)} column(s): " + ", ".join(
            f"{c.get('name')} {c.get('type_text')}" for c in columns[:40]
        )
        return ToolResult(
            evidence=[
                _evidence(
                    resource=f"unity-catalog/{full_name}",
                    kind="schema",
                    summary=summary,
                    citation="EV-SCHEMA",
                    subject=subject,
                    event_at=_ms(table.get("updated_at")),
                )
            ]
        )

    return (
        ToolContract(
            name="databricks.get_run",
            purpose="Retrieve a job run, its tasks, and which task failed first.",
            risk_class=RiskClass.READ,
            required_permission="jobs:read",
            input_schema={
                "type": "object",
                "properties": {"job_id": {"type": "string"}, "run_id": {"type": "string"}},
            },
            fn=get_run,
        ),
        ToolContract(
            name="databricks.get_task_output",
            purpose="Retrieve the error and stack trace of a run's failed tasks.",
            risk_class=RiskClass.READ,
            required_permission="jobs:read",
            input_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}, "task_key": {"type": "string"}},
                "required": ["run_id"],
            },
            timeout_ms=30_000,
            fn=get_task_output,
        ),
        ToolContract(
            name="databricks.compare_runs",
            purpose="Diff the last successful run against the first failed run.",
            risk_class=RiskClass.READ,
            required_permission="jobs:read",
            input_schema={"type": "object", "properties": {"job_id": {"type": "string"}}},
            fn=compare_runs,
        ),
        ToolContract(
            name="databricks.get_job_config",
            purpose="Retrieve a job's task graph, schedule and settings.",
            risk_class=RiskClass.READ,
            required_permission="jobs:read",
            input_schema={"type": "object", "properties": {"job_id": {"type": "string"}}},
            fn=get_job_config,
        ),
        ToolContract(
            name="catalog.get_schema",
            purpose="Retrieve a Unity Catalog table's current column types.",
            risk_class=RiskClass.READ,
            required_permission="catalog:read",
            input_schema={
                "type": "object",
                "properties": {"table": {"type": "string"}},
                "required": ["table"],
            },
            fn=get_schema,
        ),
    )
