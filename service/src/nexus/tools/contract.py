"""Tool contract (SDD 7 outbound, NX-010).

Every tool declares its permission, risk class, timeout and cost hint. The
gateway reads risk_class from here, so a connector cannot smuggle a write past
the policy engine by mislabelling itself at call time.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from nexus.domain.evidence import Evidence
from nexus.domain.models import ResourceRef, Subject
from nexus.governance.pdp import RiskClass


@dataclass(frozen=True, slots=True)
class ToolCall:
    tool_name: str
    resource: ResourceRef
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    evidence: list[Evidence]
    raw_ref: str | None = None
    truncated: bool = False


#: A connector implementation. Receives the subject so every read is performed
#: with the invoking user's identity where the platform supports delegation.
ToolFn = Callable[[Subject, ToolCall], Awaitable[ToolResult]]


@dataclass(frozen=True, slots=True)
class ToolContract:
    name: str
    purpose: str
    risk_class: RiskClass
    required_permission: str
    input_schema: dict[str, Any]
    timeout_ms: int = 20_000
    cost_hint: str = "low"
    max_output_bytes: int = 65_536
    fn: ToolFn | None = None

    def __post_init__(self) -> None:
        if self.risk_class is not RiskClass.READ:
            # Phase 1-6 admit no write-capable tool into the registry at all.
            # This is the credential/contract layer of the defence in depth
            # described in SDD 4.1; the PDP is a separate, later layer.
            raise ValueError(
                f"tool {self.name!r} declares risk_class {self.risk_class}; "
                "the MVP registry admits READ tools only"
            )

    def validate_arguments(self, arguments: dict[str, Any]) -> list[str]:
        """Minimal structural check. Phase 2 replaces this with full JSON Schema."""
        errors: list[str] = []
        required = self.input_schema.get("required", [])
        for key in required:
            if key not in arguments:
                errors.append(f"missing required argument {key!r}")
        properties = self.input_schema.get("properties", {})
        for key in arguments:
            if properties and key not in properties:
                errors.append(f"unexpected argument {key!r}")
        return errors
