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
import time
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import count

from nexus.agent.budget import BudgetExceeded, BudgetTracker
from nexus.api.errors import ErrorCode, NexusError
from nexus.domain.evidence import Evidence, MissingEvidence
from nexus.domain.models import Sensitivity, StepOutcome, Subject
from nexus.governance.pdp import PolicyDecisionPoint, PolicyRequest
from nexus.observability.logging import get_logger
from nexus.observability.trace import NullTraceSink, TraceEvent, TraceSink, hash_arguments, utcnow
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
        trace: TraceSink | None = None,
    ) -> None:
        self._registry = registry
        self._gateway = gateway
        self._pdp = pdp
        self._budget = budget
        self._fanout = fanout
        self._trace = trace or NullTraceSink()
        self._seq = count(1)

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
        attempted: set[str] = set()

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
                _report_unattempted(plan, attempted, result, result.stop_reason)
                return result

            before = len(result.evidence)
            # return_exceptions: one step raising must not cancel the caller's
            # await and orphan its siblings, which keep running and mutating a
            # result nobody is reading any more.
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
                ),
                return_exceptions=True,
            )
            outcomes = [
                StepOutcome.UNAVAILABLE if isinstance(o, BaseException) else o for o in outcomes
            ]
            result.steps_run += len(wave)

            attempted.update(s.id for s in wave)

            for step, outcome in zip(wave, outcomes, strict=True):
                if outcome is not StepOutcome.OK and step.essential:
                    result.stop_reason = StopReason.ESSENTIAL_STEP_DENIED
                    _report_unattempted(plan, attempted, result, result.stop_reason)
                    return result

            barren_rounds = barren_rounds + 1 if len(result.evidence) == before else 0
            if barren_rounds >= 2:
                result.stop_reason = StopReason.NO_NEW_EVIDENCE
                _report_unattempted(plan, attempted, result, result.stop_reason)
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
            # Per step, not only per wave. A wave is bounded by dependency
            # structure, not by fanout, so a single wave of independent steps
            # could otherwise blow through the ceiling between two wave-level
            # checks.
            try:
                self._budget.check()
            except BudgetExceeded as exc:
                result.missing.append(
                    MissingEvidence(
                        what=step.why,
                        why=str(exc),
                        remediation="Raise the budget or narrow the question, then re-run.",
                    )
                )
                return StepOutcome.UNAVAILABLE
            self._budget.record_step()
            seq = next(self._seq)
            started_at = utcnow()
            started = time.monotonic()
            contract = self._registry.get(step.call.tool_name)
            if contract is None:
                await self._emit(
                    subject,
                    investigation_id,
                    seq,
                    step,
                    started_at,
                    started,
                    outcome=StepOutcome.UNAVAILABLE,
                    error_class="RESOURCE_NOT_FOUND",
                )
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
                outcome = (
                    StepOutcome.DENIED
                    if exc.code in {ErrorCode.POLICY_DENIED, ErrorCode.AUTHZ_DENIED}
                    else StepOutcome.UNAVAILABLE
                )
                await self._emit(
                    subject,
                    investigation_id,
                    seq,
                    step,
                    started_at,
                    started,
                    outcome=outcome,
                    error_class=str(exc.code),
                    decision_id=decision.id,
                )
                return outcome
            except Exception as exc:  # noqa: BLE001
                # Anything that is not a NexusError - notably AuditWriteFailed,
                # which is a RuntimeError - would otherwise escape the step,
                # take down the whole wave, and orphan its siblings. One step
                # failing is a gap in the evidence, never the end of the
                # investigation.
                log.exception("step_failed", investigation_id=investigation_id, step=step.id)
                result.missing.append(
                    MissingEvidence(
                        what=step.why,
                        why=f"{type(exc).__name__}: {exc}",
                        source_system=step.call.resource.system,
                    )
                )
                await self._emit(
                    subject,
                    investigation_id,
                    seq,
                    step,
                    started_at,
                    started,
                    outcome=StepOutcome.UNAVAILABLE,
                    error_class=type(exc).__name__,
                    decision_id=decision.id,
                )
                return StepOutcome.UNAVAILABLE

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
            await self._emit(
                subject,
                investigation_id,
                seq,
                step,
                started_at,
                started,
                outcome=outcome,
                decision_id=decision.id,
            )
            return outcome

    async def _emit(
        self,
        subject: Subject,
        investigation_id: str,
        seq: int,
        step: PlanStep,
        started_at: object,
        started_monotonic: float,
        *,
        outcome: StepOutcome,
        error_class: str | None = None,
        decision_id: str | None = None,
    ) -> None:
        """Persisting the trace must never break the investigation."""
        try:
            await self._trace.record(
                TraceEvent(
                    investigation_id=investigation_id,
                    tenant_id=subject.tenant_id,
                    seq=seq,
                    step_type="tool_call",
                    tool_name=step.call.tool_name,
                    input_hash=hash_arguments(step.call.arguments),
                    policy_decision_id=decision_id,
                    outcome=str(outcome),
                    error_class=error_class,
                    latency_ms=int((time.monotonic() - started_monotonic) * 1000),
                    started_at=started_at,  # type: ignore[arg-type]
                    ended_at=utcnow(),
                )
            )
        except Exception:  # noqa: BLE001 - trace loss must not fail the work
            log.exception("trace_write_failed", investigation_id=investigation_id, seq=seq)


def _report_unattempted(
    plan: list[PlanStep],
    attempted: set[str],
    result: LoopResult,
    stop_reason: StopReason,
) -> None:
    """A step the loop never reached is still a gap in the evidence.

    Without this, an investigation that stopped after its first wave looks
    exactly like one that ran its whole plan.
    """
    for step in plan:
        if step.id not in attempted:
            result.missing.append(
                MissingEvidence(
                    what=step.why,
                    why=f"not attempted: the investigation stopped early ({stop_reason})",
                    source_system=step.call.resource.system,
                )
            )


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
