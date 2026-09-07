"""Governed tool gateway - the single entry point (ADR-03, NX-040, SC-14).

INVARIANT
---------
There is exactly one way to invoke a tool, and it requires a PolicyDecision
with effect=PERMIT whose binding matches this exact (subject, tool, resource,
investigation) tuple and which has not expired.

There is no bypass path, no admin flag, and no test hook. Tests exercise the
same entry point as production.

A second invariant: an unauditable tool call must not happen. The audit record
is written before the result is returned, and a failed audit write raises
rather than letting an unrecorded read succeed.
"""

from __future__ import annotations

import asyncio
import time

from nexus.api.errors import ErrorCode, NexusError
from nexus.domain.models import StepOutcome, Subject
from nexus.governance.audit import AuditAction, AuditRecord, AuditSink, AuditWriteFailed
from nexus.governance.pdp import PolicyDecision, binding_for
from nexus.observability.logging import get_logger
from nexus.tools.contract import ToolCall, ToolResult
from nexus.tools.registry import ToolRegistry

log = get_logger(__name__)


class ToolGateway:
    def __init__(self, registry: ToolRegistry, audit: AuditSink) -> None:
        self._registry = registry
        self._audit = audit

    async def invoke(
        self,
        *,
        subject: Subject,
        call: ToolCall,
        decision: PolicyDecision,
        investigation_id: str,
        purpose: str,
    ) -> tuple[ToolResult | None, StepOutcome]:
        contract = self._registry.get(call.tool_name)
        if contract is None or contract.fn is None:
            raise NexusError(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"tool {call.tool_name!r} is not registered",
                remediation="Register the tool contract before invoking it.",
            )

        # --- the invariant -------------------------------------------------
        self._enforce_decision(
            subject=subject,
            call=call,
            decision=decision,
            investigation_id=investigation_id,
        )
        # -------------------------------------------------------------------

        errors = contract.validate_arguments(call.arguments)
        if errors:
            await self._write_audit(
                subject, call, decision, investigation_id, purpose, "schema_rejected"
            )
            raise NexusError(
                ErrorCode.SCHEMA_VALIDATION_FAILED,
                "; ".join(errors),
                remediation="Correct the tool arguments to match the declared input schema.",
            )

        started = time.monotonic()
        outcome = StepOutcome.OK
        result: ToolResult | None = None
        try:
            result = await asyncio.wait_for(
                contract.fn(subject, call), timeout=contract.timeout_ms / 1000
            )
        except TimeoutError:
            outcome = StepOutcome.TIMEOUT
        except NexusError:
            outcome = StepOutcome.UNAVAILABLE
        except Exception:  # noqa: BLE001 - connectors must not crash the loop
            log.exception("tool_unhandled_error", tool=call.tool_name)
            outcome = StepOutcome.UNAVAILABLE
        else:
            if not result.evidence:
                outcome = StepOutcome.EMPTY
            elif result.truncated:
                outcome = StepOutcome.TRUNCATED

        elapsed_ms = int((time.monotonic() - started) * 1000)

        # Audit before returning. A failed write aborts the operation.
        await self._write_audit(subject, call, decision, investigation_id, purpose, str(outcome))

        log.info(
            "tool_invoked",
            tool=call.tool_name,
            resource=call.resource.uri,
            outcome=str(outcome),
            latency_ms=elapsed_ms,
            decision_id=decision.id,
        )
        return result, outcome

    def _enforce_decision(
        self,
        *,
        subject: Subject,
        call: ToolCall,
        decision: PolicyDecision,
        investigation_id: str,
    ) -> None:
        if not decision.permitted:
            raise NexusError(
                ErrorCode.POLICY_DENIED,
                f"policy {decision.policy_id} denied this call: {decision.reason}",
                remediation="The agent must report the denial, not route around it.",
            )
        if decision.is_expired():
            raise NexusError(
                ErrorCode.POLICY_DENIED,
                "policy decision has expired",
                remediation="Re-evaluate policy immediately before the call.",
            )

        contract = self._registry.get(call.tool_name)
        assert contract is not None  # checked by the caller
        from nexus.governance.pdp import PolicyRequest  # local import: avoids a cycle

        expected = binding_for(
            PolicyRequest(
                subject=subject,
                tool_name=call.tool_name,
                risk_class=contract.risk_class,
                resource=call.resource,
                purpose="",
                investigation_id=investigation_id,
            )
        )
        if decision.binding != expected:
            raise NexusError(
                ErrorCode.POLICY_DENIED,
                "policy decision does not bind to this call",
                remediation=(
                    "A decision authorizes exactly one (subject, tool, resource, "
                    "investigation) tuple and cannot be reused for another."
                ),
            )

    async def _write_audit(
        self,
        subject: Subject,
        call: ToolCall,
        decision: PolicyDecision,
        investigation_id: str,
        purpose: str,
        result_status: str,
    ) -> None:
        try:
            await self._audit.record(
                AuditRecord(
                    action=AuditAction.TOOL_INVOKE,
                    subject_id=subject.user_id,
                    tenant_id=subject.tenant_id,
                    resource=call.resource.uri,
                    purpose=purpose,
                    result_status=result_status,
                    investigation_id=investigation_id,
                    policy_id=decision.policy_id,
                    decision=str(decision.effect),
                    reason=decision.reason,
                )
            )
        except Exception as exc:
            raise AuditWriteFailed(
                "audit write failed; the tool call must not be treated as successful"
            ) from exc
