"""Durable audit and trace, and real usage metering (Phase 1 criteria 4 and 8)."""

from __future__ import annotations

from nexus.agent.budget import Budget, BudgetTracker
from nexus.agent.metering import MeteredModelAdapter
from nexus.agent.model import ModelMessage, ModelTier
from nexus.agent.providers.echo import EchoModelAdapter
from nexus.db.repository import AuditRepository, TraceRepository
from nexus.db.session import get_session
from nexus.observability.trace import InMemoryTraceSink, hash_arguments

BODY = {
    "intent": "diagnose_job_failure",
    "question": "Why did customer_daily_ingestion fail?",
    "resource_refs": [{"type": "databricks_job", "id": "1234", "workspace": "ws"}],
}


async def test_audit_survives_in_the_database_not_process_memory(client, auth):
    created = (await client.post("/v1/investigations", json=BODY, headers=auth)).json()

    async with get_session() as session:
        rows = await AuditRepository(session).list_for_investigation(
            tenant_id="pilot-a", investigation_id=created["id"]
        )
    assert len(rows) == 3
    assert {r.action for r in rows} == {"tool.invoke"}
    assert all(r.decision == "permit" for r in rows)


async def test_audit_is_not_readable_from_another_tenant(client, auth):
    created = (await client.post("/v1/investigations", json=BODY, headers=auth)).json()
    other = {**auth, "X-Nexus-Tenant": "pilot-b"}
    entries = (await client.get(f"/v1/investigations/{created['id']}/audit", headers=other)).json()
    assert entries == []


async def test_trace_steps_are_persisted(client, auth):
    created = (await client.post("/v1/investigations", json=BODY, headers=auth)).json()

    async with get_session() as session:
        steps = await TraceRepository(session).list_for_investigation(
            tenant_id="pilot-a", investigation_id=created["id"]
        )
    assert len(steps) == 3
    assert [s.seq for s in steps] == [1, 2, 3]
    assert all(s.step_type == "tool_call" for s in steps)
    assert all(s.outcome == "ok" for s in steps)
    assert all(s.policy_decision_id for s in steps)
    assert all(s.latency_ms is not None for s in steps)
    # arguments are fingerprinted, never stored
    assert all(s.input_hash and len(s.input_hash) == 64 for s in steps)


async def test_trace_records_a_denied_step(registry, gateway, pdp, subject):
    from nexus.agent.loop import InvestigationLoop, PlanStep
    from nexus.domain.models import ResourceRef
    from nexus.tools.contract import ToolCall

    sink = InMemoryTraceSink()
    budget = BudgetTracker(
        Budget(
            wall_clock_ms=300_000,
            tool_calls=25,
            plan_steps=15,
            replans=2,
            tokens_in=150_000,
            tokens_out=20_000,
        )
    )
    loop = InvestigationLoop(registry=registry, gateway=gateway, pdp=pdp, budget=budget, trace=sink)
    outside = ResourceRef(system="databricks", resource_id="other-ws/jobs/1")
    await loop.run(
        subject=subject,
        investigation_id="inv-1",
        purpose="p",
        plan=[PlanStep("s1", ToolCall("mock.databricks.get_run", outside), "check")],
    )
    events = sink.events()
    assert len(events) == 1
    assert events[0].outcome == "denied"
    assert events[0].error_class == "POLICY_DENIED"


def test_argument_hash_is_stable_and_order_independent():
    a = hash_arguments({"run_id": "1", "task": "t"})
    b = hash_arguments({"task": "t", "run_id": "1"})
    assert a == b
    assert a != hash_arguments({"run_id": "2", "task": "t"})


async def test_model_usage_is_metered_into_the_budget():
    budget = BudgetTracker(
        Budget(
            wall_clock_ms=300_000,
            tool_calls=25,
            plan_steps=15,
            replans=2,
            tokens_in=150_000,
            tokens_out=20_000,
        )
    )
    metered = MeteredModelAdapter(EchoModelAdapter(), budget, investigation_id="inv-1")
    await metered.complete([ModelMessage(role="user", content="a" * 400)], tier=ModelTier.SMALL)
    snap = budget.snapshot()
    assert snap["tokens_in"] > 0
    assert snap["tokens_out"] > 0
    assert metered.calls == 1


async def test_investigation_reports_non_zero_token_usage(client, auth):
    """Criterion 8: usage must actually be visible, not structurally always zero."""
    created = (await client.post("/v1/investigations", json=BODY, headers=auth)).json()
    body = (await client.get(f"/v1/investigations/{created['id']}", headers=auth)).json()

    assert body["consumed"]["tokens_in"] > 0
    assert body["consumed"]["tokens_out"] > 0
    assert body["observation_summary"]
