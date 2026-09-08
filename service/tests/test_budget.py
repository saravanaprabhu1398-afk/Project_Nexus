"""Budgets (NX-012, SDD 9.6). Exhaustion is a reported partial result."""

from __future__ import annotations

import pytest

from nexus.agent.budget import BudgetExceeded, BudgetTracker
from tests.conftest import make_budget


def test_tool_call_ceiling_is_enforced():
    t = BudgetTracker(make_budget(tool_calls=2))
    t.check()
    t.record_tool_call()
    t.check()
    t.record_tool_call()
    with pytest.raises(BudgetExceeded) as exc:
        t.check()
    assert exc.value.dimension == "tool_calls"


def test_token_ceiling_is_enforced():
    t = BudgetTracker(make_budget(tokens_in=100))
    t.record_tokens(150, 10)
    with pytest.raises(BudgetExceeded) as exc:
        t.check()
    assert exc.value.dimension == "tokens_in"


def test_replan_ceiling_matches_every_other_dimension():
    """check() gates the next unit of work, so consumed == limit means stop.

    This previously used `>` where every other dimension used `>=`, quietly
    allowing one replan more than configured - and the old test encoded that
    off-by-one as the expected behaviour.
    """
    t = BudgetTracker(make_budget(replans=2))
    t.check()  # 0 used - a replan is allowed
    t.record_replan()
    t.check()  # 1 used - one more is allowed
    t.record_replan()
    with pytest.raises(BudgetExceeded) as exc:  # 2 used - the limit is reached
        t.check()
    assert exc.value.dimension == "replans"


def test_every_dimension_stops_at_its_limit_not_one_past_it():
    """Guards the consistency itself: no dimension may be more generous."""
    cases = [
        ("tool_calls", lambda t: t.record_tool_call()),
        ("plan_steps", lambda t: t.record_step()),
        ("replans", lambda t: t.record_replan()),
    ]
    for dimension, record in cases:
        t = BudgetTracker(make_budget(**{dimension: 1}))
        t.check()
        record(t)
        with pytest.raises(BudgetExceeded) as exc:
            t.check()
        assert exc.value.dimension == dimension, f"{dimension} allowed one too many"


def test_snapshot_reports_every_dimension():
    t = BudgetTracker(make_budget())
    t.record_tool_call()
    t.record_step()
    t.record_tokens(10, 5)
    snap = t.snapshot()
    assert snap["tool_calls"] == 1
    assert snap["plan_steps"] == 1
    assert snap["tokens_in"] == 10
    assert "elapsed_ms" in snap
