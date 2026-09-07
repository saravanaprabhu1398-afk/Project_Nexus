"""The gateway invariant (ADR-03, NX-040, SC-14, SC-15).

These tests exist to make the invariant expensive to break. If someone adds a
bypass path to the gateway, one of these fails.
"""

from __future__ import annotations

import pytest

from nexus.api.errors import ErrorCode, NexusError
from nexus.governance.pdp import (
    DECISION_TTL,
    Effect,
    PolicyDecision,
    PolicyRequest,
    RiskClass,
    binding_for,
)
from nexus.tools.contract import ToolCall, ToolContract


async def _permit(pdp, subject, resource, tool="mock.databricks.get_run", inv="inv-1"):
    return await pdp.evaluate(
        PolicyRequest(
            subject=subject,
            tool_name=tool,
            risk_class=RiskClass.READ,
            resource=resource,
            purpose="diagnose_job_failure",
            investigation_id=inv,
        )
    )


async def test_permit_allows_the_call(gateway, pdp, subject, resource):
    decision = await _permit(pdp, subject, resource)
    assert decision.effect is Effect.PERMIT

    result, outcome = await gateway.invoke(
        subject=subject,
        call=ToolCall("mock.databricks.get_run", resource, {"run_id": "run-1842"}),
        decision=decision,
        investigation_id="inv-1",
        purpose="diagnose_job_failure",
    )
    assert outcome == "ok"
    assert result is not None and result.evidence


async def test_deny_blocks_the_call(gateway, pdp, subject, resource):
    """A DENY decision cannot be passed off as authorization."""
    denied = PolicyDecision(
        effect=Effect.DENY,
        policy_id="static-v1/tool_allowlist",
        reason="not registered",
        binding="whatever",
    )
    with pytest.raises(NexusError) as exc:
        await gateway.invoke(
            subject=subject,
            call=ToolCall("mock.databricks.get_run", resource, {"run_id": "r"}),
            decision=denied,
            investigation_id="inv-1",
            purpose="p",
        )
    assert exc.value.code is ErrorCode.POLICY_DENIED


async def test_decision_for_another_resource_is_refused(gateway, pdp, subject, resource):
    """A PERMIT is bound to one (subject, tool, resource, investigation) tuple.

    Reusing it against a different resource is the classic confused-deputy
    escalation, and it must not work.
    """
    from nexus.domain.models import ResourceRef

    decision = await _permit(pdp, subject, resource)
    other = ResourceRef(system="databricks", resource_id="ws/jobs/9999")

    with pytest.raises(NexusError) as exc:
        await gateway.invoke(
            subject=subject,
            call=ToolCall("mock.databricks.get_run", other, {"run_id": "r"}),
            decision=decision,
            investigation_id="inv-1",
            purpose="p",
        )
    assert exc.value.code is ErrorCode.POLICY_DENIED
    assert "does not bind" in exc.value.message


async def test_decision_for_another_investigation_is_refused(gateway, pdp, subject, resource):
    decision = await _permit(pdp, subject, resource, inv="inv-1")
    with pytest.raises(NexusError):
        await gateway.invoke(
            subject=subject,
            call=ToolCall("mock.databricks.get_run", resource, {"run_id": "r"}),
            decision=decision,
            investigation_id="inv-2",
            purpose="p",
        )


async def test_expired_decision_is_refused(gateway, subject, resource):
    from datetime import UTC, datetime

    stale = PolicyDecision(
        effect=Effect.PERMIT,
        policy_id="static-v1/permit_read_in_scope",
        reason="ok",
        binding=binding_for(
            PolicyRequest(
                subject=subject,
                tool_name="mock.databricks.get_run",
                risk_class=RiskClass.READ,
                resource=resource,
                purpose="",
                investigation_id="inv-1",
            )
        ),
        issued_at=datetime.now(UTC) - DECISION_TTL * 2,
    )
    with pytest.raises(NexusError) as exc:
        await gateway.invoke(
            subject=subject,
            call=ToolCall("mock.databricks.get_run", resource, {"run_id": "r"}),
            decision=stale,
            investigation_id="inv-1",
            purpose="p",
        )
    assert "expired" in exc.value.message


async def test_write_tool_cannot_be_constructed():
    """SC-15: the registry admits READ tools only.

    This is the contract layer of the defence in depth - it fails before the
    PDP is ever consulted.
    """
    with pytest.raises(ValueError, match="READ tools only"):
        ToolContract(
            name="databricks.restart_job",
            purpose="restart a failed job",
            risk_class=RiskClass.EXECUTE,
            required_permission="jobs:run",
            input_schema={},
        )


async def test_resource_outside_pilot_scope_is_denied(pdp, subject):
    from nexus.domain.models import ResourceRef

    outside = ResourceRef(system="databricks", resource_id="other-ws/jobs/1")
    decision = await pdp.evaluate(
        PolicyRequest(
            subject=subject,
            tool_name="mock.databricks.get_run",
            risk_class=RiskClass.READ,
            resource=outside,
            purpose="p",
            investigation_id="inv-1",
        )
    )
    assert decision.effect is Effect.DENY
    assert "resource_scope" in decision.policy_id


async def test_unregistered_tool_is_denied(pdp, subject, resource):
    decision = await pdp.evaluate(
        PolicyRequest(
            subject=subject,
            tool_name="databricks.delete_everything",
            risk_class=RiskClass.READ,
            resource=resource,
            purpose="p",
            investigation_id="inv-1",
        )
    )
    assert decision.effect is Effect.DENY
    assert "tool_allowlist" in decision.policy_id


async def test_every_invocation_is_audited(gateway, pdp, audit, subject, resource):
    """SC-14: 100% of tool calls audited - true from Phase 1, not Phase 4."""
    decision = await _permit(pdp, subject, resource)
    await gateway.invoke(
        subject=subject,
        call=ToolCall("mock.databricks.get_run", resource, {"run_id": "r"}),
        decision=decision,
        investigation_id="inv-1",
        purpose="diagnose_job_failure",
    )
    entries = audit.entries()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.subject_id == subject.user_id
    assert entry.tenant_id == subject.tenant_id
    assert entry.resource == resource.uri
    assert entry.purpose == "diagnose_job_failure"
    assert entry.policy_id == decision.policy_id
