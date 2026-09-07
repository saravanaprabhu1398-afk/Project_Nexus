"""Investigation budgets (NX-012, SDD 9.6).

Budget exhaustion produces a partial result with an explicit reason, never a
silent truncation and never an unbounded loop.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class Budget:
    wall_clock_ms: int
    tool_calls: int
    plan_steps: int
    replans: int
    tokens_in: int
    tokens_out: int


@dataclass(slots=True)
class Consumption:
    tool_calls: int = 0
    plan_steps: int = 0
    replans: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    started_monotonic: float = field(default_factory=time.monotonic)

    @property
    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.started_monotonic) * 1000)


class BudgetExceeded(Exception):
    def __init__(self, dimension: str, limit: int, consumed: int) -> None:
        super().__init__(f"budget exhausted on {dimension}: consumed {consumed} of {limit}")
        self.dimension = dimension
        self.limit = limit
        self.consumed = consumed


class BudgetTracker:
    def __init__(self, budget: Budget) -> None:
        self.budget = budget
        self.consumed = Consumption()

    def check(self) -> None:
        """Raise if any dimension is exhausted. Called before each step."""
        c, b = self.consumed, self.budget
        if c.elapsed_ms >= b.wall_clock_ms:
            raise BudgetExceeded("wall_clock_ms", b.wall_clock_ms, c.elapsed_ms)
        if c.tool_calls >= b.tool_calls:
            raise BudgetExceeded("tool_calls", b.tool_calls, c.tool_calls)
        if c.plan_steps >= b.plan_steps:
            raise BudgetExceeded("plan_steps", b.plan_steps, c.plan_steps)
        if c.replans > b.replans:
            raise BudgetExceeded("replans", b.replans, c.replans)
        if c.tokens_in >= b.tokens_in:
            raise BudgetExceeded("tokens_in", b.tokens_in, c.tokens_in)
        if c.tokens_out >= b.tokens_out:
            raise BudgetExceeded("tokens_out", b.tokens_out, c.tokens_out)

    def record_tool_call(self) -> None:
        self.consumed.tool_calls += 1

    def record_step(self) -> None:
        self.consumed.plan_steps += 1

    def record_replan(self) -> None:
        self.consumed.replans += 1

    def record_tokens(self, tokens_in: int, tokens_out: int) -> None:
        self.consumed.tokens_in += tokens_in
        self.consumed.tokens_out += tokens_out

    def snapshot(self) -> dict[str, int]:
        c = self.consumed
        return {
            "tool_calls": c.tool_calls,
            "plan_steps": c.plan_steps,
            "replans": c.replans,
            "tokens_in": c.tokens_in,
            "tokens_out": c.tokens_out,
            "elapsed_ms": c.elapsed_ms,
        }
