"""Budgets (NX-012, SDD 9.6). Exhaustion is a reported partial result."""

from __future__ import annotations

import pytest

from nexus.agent.budget import Budget, BudgetExceeded, BudgetTracker


def _budget(**overrides) -> Budget:
    base = dict(
        wall_clock_ms=300_000,
        tool_calls=3,
        plan_steps=15,
        replans=2,
        tokens_in=1000,
        tokens_out=1000,
    )
    base.update(overrides)
    return Budget(**base)


def test_tool_call_ceiling_is_enforced():
    t = BudgetTracker(_budget(tool_calls=2))
    t.check()
    t.record_tool_call()
    t.check()
    t.record_tool_call()
    with pytest.raises(BudgetExceeded) as exc:
        t.check()
    assert exc.value.dimension == "tool_calls"


def test_token_ceiling_is_enforced():
    t = BudgetTracker(_budget(tokens_in=100))
    t.record_tokens(150, 10)
    with pytest.raises(BudgetExceeded) as exc:
        t.check()
    assert exc.value.dimension == "tokens_in"


def test_replan_ceiling_allows_the_limit_and_rejects_beyond():
    t = BudgetTracker(_budget(replans=2))
    for _ in range(2):
        t.record_replan()
    t.check()
    t.record_replan()
    with pytest.raises(BudgetExceeded):
        t.check()


def test_snapshot_reports_every_dimension():
    t = BudgetTracker(_budget())
    t.record_tool_call()
    t.record_step()
    t.record_tokens(10, 5)
    snap = t.snapshot()
    assert snap["tool_calls"] == 1
    assert snap["plan_steps"] == 1
    assert snap["tokens_in"] == 10
    assert "elapsed_ms" in snap
