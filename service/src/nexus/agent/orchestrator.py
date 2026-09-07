"""Investigation orchestrator (NX-005, NX-006).

Owns the state machine and the async execution of an investigation. The API
returns as soon as the record exists (ADR-01); this runs afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass

from nexus.agent.budget import Budget, BudgetExceeded, BudgetTracker
from nexus.agent.loop import InvestigationLoop, LoopResult, PlanStep, StopReason
from nexus.agent.metering import MeteredModelAdapter
from nexus.agent.model import ModelAdapter, ModelMessage, ModelTier, quarantine
from nexus.config import Settings
from nexus.domain.models import InvestigationStatus, ResourceRef, Sensitivity, Subject
from nexus.governance.pdp import PolicyDecisionPoint
from nexus.observability.logging import get_logger
from nexus.observability.trace import NullTraceSink, TraceSink
from nexus.tools.contract import ToolCall
from nexus.tools.gateway import ToolGateway
from nexus.tools.registry import ToolRegistry

log = get_logger(__name__)


@dataclass(slots=True)
class InvestigationOutcome:
    status: InvestigationStatus
    loop: LoopResult
    consumed: dict[str, int]
    failure_code: str | None = None
    observation_summary: str | None = None


class Orchestrator:
    def __init__(
        self,
        *,
        settings: Settings,
        registry: ToolRegistry,
        gateway: ToolGateway,
        pdp: PolicyDecisionPoint,
        model: ModelAdapter,
        trace: TraceSink | None = None,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._gateway = gateway
        self._pdp = pdp
        self._model = model
        self._trace = trace or NullTraceSink()

    def _budget(self) -> BudgetTracker:
        s = self._settings
        return BudgetTracker(
            Budget(
                wall_clock_ms=s.budget_wall_clock_ms,
                tool_calls=s.budget_tool_calls,
                plan_steps=s.budget_plan_steps,
                replans=s.budget_replans,
                tokens_in=s.budget_tokens_in,
                tokens_out=s.budget_tokens_out,
            )
        )

    async def run(
        self,
        *,
        subject: Subject,
        investigation_id: str,
        intent: str,
        resource: ResourceRef,
        sensitivity_ceiling: Sensitivity = Sensitivity.CONFIDENTIAL,
    ) -> InvestigationOutcome:
        if self._settings.disabled:
            # Kill switch checked at start and before each call (SDD 8.4).
            return InvestigationOutcome(
                status=InvestigationStatus.ABORTED,
                loop=LoopResult(stop_reason=StopReason.NEEDS_INPUT),
                consumed={},
                failure_code="SERVICE_DISABLED",
            )

        budget = self._budget()
        loop = InvestigationLoop(
            registry=self._registry,
            gateway=self._gateway,
            pdp=self._pdp,
            budget=budget,
            fanout=self._settings.tool_fanout,
            trace=self._trace,
        )

        plan = self._static_plan(resource)
        result = await loop.run(
            subject=subject,
            investigation_id=investigation_id,
            purpose=intent,
            plan=plan,
            sensitivity_ceiling=sensitivity_ceiling,
        )

        model = MeteredModelAdapter(self._model, budget, investigation_id=investigation_id)
        summary = await self._summarize(model, result)

        status = (
            InvestigationStatus.COMPLETE if result.evidence else InvestigationStatus.NEEDS_INPUT
        )
        log.info(
            "investigation_finished",
            investigation_id=investigation_id,
            status=str(status),
            stop_reason=str(result.stop_reason),
            evidence_count=len(result.evidence),
            missing_count=len(result.missing),
            **budget.snapshot(),
        )
        return InvestigationOutcome(
            status=status,
            loop=result,
            consumed=budget.snapshot(),
            observation_summary=summary,
        )

    async def _summarize(self, model: MeteredModelAdapter, result: LoopResult) -> str | None:
        """State what the evidence reports. This is NOT a diagnosis.

        Root-cause reasoning, confidence banding and the guardrail that rejects
        unbound claims are Phase 3 (NX-081, NX-082, NX-087). What this exists to
        do in Phase 1 is exercise the model path end to end, so token, latency
        and cost telemetry are real rather than structurally always zero, and so
        the untrusted-content wrapper sits on the path from the first model call
        rather than being added over it later.
        """
        if not result.evidence:
            return None

        evidence_block = "\n".join(
            f"[{e.citation_key}] {e.source_system} {e.evidence_type}: {e.content_summary}"
            for e in result.evidence
        )
        messages = [
            ModelMessage(
                role="system",
                content=(
                    "State only what the evidence below reports. Do not infer a "
                    "cause and do not add anything the evidence does not say. "
                    "Refer to items by their citation key."
                ),
            ),
            ModelMessage(role="user", content=quarantine(evidence_block, source="tool_output")),
        ]
        try:
            response = await model.complete(messages, tier=ModelTier.SMALL)
        except BudgetExceeded:
            log.info("summary_skipped_budget_exhausted")
            return None
        except Exception:  # noqa: BLE001 - a model failure degrades, never crashes
            log.exception("summary_model_call_failed")
            return None
        return response.text

    def _static_plan(self, resource: ResourceRef) -> list[PlanStep]:
        """Phase 1 stand-in for the Planner (NX-075).

        The shape is the real one: typed steps with declared dependencies, so
        the executor's wave logic is exercised before the Planner exists.
        """
        return [
            PlanStep(
                id="s1",
                call=ToolCall(
                    tool_name="mock.databricks.get_run",
                    resource=resource,
                    arguments={"run_id": "run-1842"},
                ),
                why="establish the failed run and which task failed first",
                essential=True,
            ),
            PlanStep(
                id="s2",
                call=ToolCall(
                    tool_name="mock.databricks.get_task_output",
                    resource=resource,
                    arguments={"run_id": "run-1842", "task_key": "transform_customers"},
                ),
                why="retrieve the exception and execution context of the failed task",
                depends_on=("s1",),
            ),
            PlanStep(
                id="s3",
                call=ToolCall(
                    tool_name="mock.databricks.compare_runs",
                    resource=resource,
                    arguments={"failed_run_id": "run-1842"},
                ),
                why="identify what changed since the last successful run",
                depends_on=("s1",),
            ),
        ]
