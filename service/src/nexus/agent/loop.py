"""The tool-calling loop (NX-011).

Phase 1 executes a static plan; the Planner that generates plans dynamically is
NX-075 in Phase 3. What is already load-bearing here and must not change:

  * policy is evaluated immediately before every call, and the decision is
    passed to the gateway (the gateway will not act without it);
  * budgets are checked before every step;
  * a non-ok step becomes a MissingEvidence entry rather than a silent gap;
  * stop conditions are explicit and enumerable.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import StrEnum

from nexus.agent.budget import BudgetExceeded, BudgetTracker
from nexus.api.errors import ErrorCode, NexusError
from nexus.domain.evidence import Evidence, MissingEvidence
from nexus.domain.models import Sensitivity, StepOutcome, Subject
from nexus.governance.pdp import PolicyDecisionPoint, PolicyRequest
from nexus.observability.logging import get_logger
from nexus.tools.contract import ToolCall
from nexus.tools.gateway import ToolGateway
from nexus.tools.registry import ToolRegistry

log = get_logger(__name__)


class StopReason(StrEnum):
    PLAN_COMPLETE = "plan_complete"
    BUDGET_EXHAUSTED = "budget_exhausted"
    NO_NEW_EVIDENCE = "no_new_evidence"
    NEEDS_INPUT = "needs_input"
    ESSENTIAL_STEP_DENIED = "essential_step_denied"


@dataclass(frozen=True, slots=True)
class PlanStep:
    id: str
    call: ToolCall
    why: str
    essential: bool = False
    depends_on: tuple[str, ...] = ()


@dataclass(slots=True)
class LoopResult:
    evidence: list[Evidence] = field(default_factory=list)
    missing: list[MissingEvidence] = field(default_factory=list)
    stop_reason: StopReason = StopReason.PLAN_COMPLETE
    steps_run: int = 0


class InvestigationLoop:
    def __init__(
        self,
        *,
        registry: ToolRegistry,
        gateway: ToolGateway,
        pdp: PolicyDecisionPoint,
        budget: BudgetTracker,
        fanout: int = 4,
    ) -> None:
        self._registry = registry
        self._gateway = gateway
        self._pdp = pdp
        self._budget = budget
        self._fanout = fanout

    async def run(
        self,
        *,
        subject: Subject,
        investigation_id: str,
        purpose: str,
        plan: list[PlanStep],
        sensitivity_ceiling: Sensitivity = Sensitivity.CONFIDENTIAL,
    ) -> LoopResult:
        result = LoopResult()
        semaphore = asyncio.Semaphore(self._fanout)
        barren_rounds = 0

        for wave in _waves(plan):
            try:
                self._budget.check()
            except BudgetExceeded as exc:
                result.stop_reason = StopReason.BUDGET_EXHAUSTED
                result.missing.append(
                    MissingEvidence(
                        what="remaining investigation steps",
                        why=str(exc),
                        remediation="Raise the budget or narrow the question, then re-run.",
                    )
                )
                return result

            before = len(result.evidence)
            outcomes = await asyncio.gather(
                *(
                    self._run_step(
                        subject=subject,
                        investigation_id=investigation_id,
                        purpose=purpose,
                        step=step,
                        sensitivity_ceiling=sensitivity_ceiling,
                        semaphore=semaphore,
                        result=result,
                    )
                    for step in wave
                )
            )
            result.steps_run += len(wave)

            for step, outcome in zip(wave, outcomes, strict=True):
                if outcome is not StepOutcome.OK and step.essential:
                    result.stop_reason = StopReason.ESSENTIAL_STEP_DENIED
                    return result

            barren_rounds = barren_rounds + 1 if len(result.evidence) == before else 0
            if barren_rounds >= 2:
                result.stop_reason = StopReason.NO_NEW_EVIDENCE
                return result

        result.stop_reason = StopReason.PLAN_COMPLETE
        return result

    async def _run_step(
        self,
        *,
        subject: Subject,
        investigation_id: str,
        purpose: str,
        step: PlanStep,
        sensitivity_ceiling: Sensitivity,
        semaphore: asyncio.Semaphore,
        result: LoopResult,
    ) -> StepOutcome:
        async with semaphore:
            self._budget.record_step()
            contract = self._registry.get(step.call.tool_name)
            if contract is None:
                result.missing.append(
                    MissingEvidence(
                        what=step.why,
                        why=f"tool {step.call.tool_name!r} is not registered",
                    )
                )
                return StepOutcome.UNAVAILABLE

            decision = await self._pdp.evaluate(
                PolicyRequest(
                    subject=subject,
                    tool_name=step.call.tool_name,
                    risk_class=contract.risk_class,
                    resource=step.call.resource,
                    purpose=purpose,
                    investigation_id=investigation_id,
                    sensitivity_ceiling=sensitivity_ceiling,
                )
            )

            self._budget.record_tool_call()
            try:
                tool_result, outcome = await self._gateway.invoke(
                    subject=subject,
                    call=step.call,
                    decision=decision,
                    investigation_id=investigation_id,
                    purpose=purpose,
                )
            except NexusError as exc:
                # A denial is reported, never routed around (SDD 9.3, stop condition 5).
                result.missing.append(
                    MissingEvidence(
                        what=step.why,
                        why=exc.message,
                        source_system=step.call.resource.system,
                        remediation=exc.remediation,
                    )
                )
                return (
                    StepOutcome.DENIED
                    if exc.code in {ErrorCode.POLICY_DENIED, ErrorCode.AUTHZ_DENIED}
                    else StepOutcome.UNAVAILABLE
                )

            if outcome is StepOutcome.OK and tool_result is not None:
                result.evidence.extend(tool_result.evidence)
            else:
                result.missing.append(
                    MissingEvidence(
                        what=step.why,
                        why=f"tool returned {outcome}",
                        source_system=step.call.resource.system,
                    )
                )
            return outcome


def _waves(plan: list[PlanStep]) -> list[list[PlanStep]]:
    """Group steps into dependency waves so independent steps run in parallel.

    Required to meet the five-minute target (SC-01); sequential tool calls
    against a slow platform will not make it.
    """
    remaining = {s.id: s for s in plan}
    done: set[str] = set()
    waves: list[list[PlanStep]] = []
    while remaining:
        ready = [s for s in remaining.values() if set(s.depends_on) <= done]
        if not ready:  # cycle or a dangling dependency; run the rest sequentially
            ready = [next(iter(remaining.values()))]
        waves.append(ready)
        for s in ready:
            done.add(s.id)
            del remaining[s.id]
    return waves
