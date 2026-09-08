"""Policy obligations must actually be carried out (security review finding 1).

Every PERMIT decision carries obligations - redact PII, cap output size. Until
now nothing read them, so the decision log recorded that redaction happened
while no redaction code ran. That is the same defect class as the token
metering with no call site, and worse than having no obligation at all,
because it reads as a working control.
"""

from __future__ import annotations

import pytest

from nexus.api.errors import ErrorCode, NexusError
from nexus.domain.models import Integrity, ResourceRef, Sensitivity, StepOutcome
from nexus.governance.pdp import PolicyRequest, RiskClass, binding_for
from nexus.governance.redaction import redact_text
from nexus.tools.contract import ToolCall


@pytest.mark.parametrize(
    ("raw", "pattern"),
    [
        ("token=sk-ant-abcdefghijklmnopqrstuv", "assignment"),
        ("Authorization: Bearer abcdefghijklmnopqrstuvwx", "bearer_token"),
        ("connect to postgres://user:hunter2@db.internal:5432/x", "url_credentials"),
        ("contact alice@example.com about it", "email"),
        ("aws key AKIAIOSFODNN7EXAMPLE denied", "aws_key"),
        ("card 4111 1111 1111 1111 declined", "card"),
    ],
)
def test_secrets_are_removed_from_free_text(raw, pattern):
    cleaned, applied = redact_text(raw)
    assert any(a.startswith(pattern) for a in applied), f"{pattern} did not match"
    for secret in (
        "hunter2",
        "sk-ant-abcdefghijklmnopqrstuv",
        "alice@example.com",
        "AKIAIOSFODNN7EXAMPLE",
        "4111 1111 1111 1111",
    ):
        if secret in raw:
            assert secret not in cleaned


def test_clean_text_is_left_alone():
    raw = "AnalysisException: cannot resolve 'customer_type' due to type mismatch"
    cleaned, applied = redact_text(raw)
    assert cleaned == raw
    assert applied == []


async def _local_gateway(contract, subject, resource, investigation_id="inv-1"):
    """A registry, PDP and gateway owned by one test.

    ToolContract is a frozen dataclass and MOCK_TOOLS is a module-level tuple,
    so mutating a shared contract leaks into every other test in the session.
    """
    from nexus.governance.audit import InMemoryAuditSink
    from nexus.governance.pdp import StaticAllowlistPDP
    from nexus.tools.gateway import ToolGateway
    from nexus.tools.registry import ToolRegistry

    registry = ToolRegistry()
    registry.register(contract)
    local_pdp = StaticAllowlistPDP(
        allowed_tools=registry.names(),
        resource_prefixes=frozenset({"databricks:ws/jobs/"}),
    )
    gateway = ToolGateway(registry, InMemoryAuditSink())
    decision = await local_pdp.evaluate(
        PolicyRequest(
            subject=subject,
            tool_name=contract.name,
            risk_class=RiskClass.READ,
            resource=resource,
            purpose="p",
            investigation_id=investigation_id,
        )
    )
    return gateway, decision


async def test_gateway_redacts_evidence_before_it_is_returned(subject, resource):
    """Log content is the highest-risk evidence source."""
    from dataclasses import replace

    from nexus.tools.mock.databricks_mock import MOCK_TOOLS

    base = next(t for t in MOCK_TOOLS if t.name.endswith("get_task_output"))

    async def leaky(subject_, call):  # noqa: ANN001
        result = await base.fn(subject_, call)
        result.evidence[0].content_summary += " (retry with token=sk-live-abcdefghijklmnop)"
        return result

    contract = replace(base, fn=leaky)
    gateway, decision = await _local_gateway(contract, subject, resource)
    assert "redact:pii" in decision.obligations

    result, outcome = await gateway.invoke(
        subject=subject,
        call=ToolCall(contract.name, resource, {"run_id": "r"}),
        decision=decision,
        investigation_id="inv-1",
        purpose="p",
    )
    assert outcome is StepOutcome.OK
    assert result is not None
    body = result.evidence[0].content_summary
    assert "sk-live-abcdefghijklmnop" not in body
    assert any(a.startswith("assignment") for a in result.evidence[0].redaction_applied)


async def test_oversized_output_is_truncated_and_labelled(subject, resource):
    from dataclasses import replace

    from nexus.tools.mock.databricks_mock import MOCK_TOOLS

    base = next(t for t in MOCK_TOOLS if t.name.endswith("get_run"))
    contract = replace(base, max_output_bytes=64)
    gateway, decision = await _local_gateway(contract, subject, resource)

    result, outcome = await gateway.invoke(
        subject=subject,
        call=ToolCall(contract.name, resource, {"run_id": "r"}),
        decision=decision,
        investigation_id="inv-1",
        purpose="p",
    )
    assert outcome is StepOutcome.TRUNCATED
    assert result is not None
    assert result.evidence[0].integrity is Integrity.TRUNCATED
    assert result.evidence[0].content_summary.endswith("[truncated]")


async def test_an_obligation_the_gateway_cannot_honour_fails_loudly(gateway, subject, resource):
    """Silently ignoring an unknown obligation is how a control becomes a lie."""
    from dataclasses import replace

    from nexus.governance.pdp import Effect, PolicyDecision

    binding = binding_for(
        PolicyRequest(
            subject=subject,
            tool_name="mock.databricks.get_run",
            risk_class=RiskClass.READ,
            resource=resource,
            purpose="",
            investigation_id="inv-1",
        )
    )
    decision = replace(
        PolicyDecision(effect=Effect.PERMIT, policy_id="test", reason="ok", binding=binding),
        obligations=("encrypt:aes256",),
    )
    with pytest.raises(NexusError) as exc:
        await gateway.invoke(
            subject=subject,
            call=ToolCall("mock.databricks.get_run", resource, {"run_id": "r"}),
            decision=decision,
            investigation_id="inv-1",
            purpose="p",
        )
    assert exc.value.code is ErrorCode.INTERNAL_ERROR
    assert "cannot honour" in exc.value.message


async def test_binding_pins_sensitivity_not_just_the_uri(pdp, subject):
    """Security review finding 2.

    A PERMIT issued for a public resource must not authorize a call against a
    restricted resource that happens to share a URI.
    """
    public = ResourceRef(
        system="databricks", resource_id="ws/jobs/1234", sensitivity=Sensitivity.PUBLIC
    )
    restricted = ResourceRef(
        system="databricks",
        resource_id="ws/jobs/1234",
        sensitivity=Sensitivity.RESTRICTED,
    )
    assert public.uri == restricted.uri

    def binding_of(ref):  # noqa: ANN001
        return binding_for(
            PolicyRequest(
                subject=subject,
                tool_name="mock.databricks.get_run",
                risk_class=RiskClass.READ,
                resource=ref,
                purpose="",
                investigation_id="inv-1",
            )
        )

    assert binding_of(public) != binding_of(restricted)

    production = ResourceRef(
        system="databricks", resource_id="ws/jobs/1234", environment="production"
    )
    assert binding_of(production) != binding_of(public)
