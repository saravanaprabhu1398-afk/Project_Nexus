"""Tool registry (NX-010).

The Planner selects tools from this registry only. A tool name appearing inside
tool output can never cause an invocation (SDD 10.5, control 2).
"""

from __future__ import annotations

from nexus.tools.contract import ToolContract


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolContract] = {}

    def register(self, contract: ToolContract) -> None:
        if contract.name in self._tools:
            raise ValueError(f"tool {contract.name!r} is already registered")
        self._tools[contract.name] = contract

    def get(self, name: str) -> ToolContract | None:
        return self._tools.get(name)

    def names(self) -> frozenset[str]:
        return frozenset(self._tools)

    def describe(self) -> list[dict[str, str]]:
        """What the Planner is allowed to see. No implementation details."""
        return [
            {"name": t.name, "purpose": t.purpose, "cost_hint": t.cost_hint}
            for t in self._tools.values()
        ]
