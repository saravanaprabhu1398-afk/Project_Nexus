"""Policy Decision Point (ADR-03, NX-038).

The interface and the decision token exist from Phase 1 so that "100% of tool
calls policy-checked" is true from the first real Databricks call in Phase 2,
not from Week 9. Phase 4 replaces StaticAllowlistPDP with the full engine
behind this same interface - the call path never changes.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from nexus.domain.models import ResourceRef, Sensitivity, Subject, exceeds_ceiling, new_id

#: A decision is bound to one call and expires. It cannot be reused or shared.
DECISION_TTL = timedelta(seconds=60)


class Effect(StrEnum):
    PERMIT = "permit"
    DENY = "deny"
    APPROVAL_REQUIRED = "approval_required"


class RiskClass(StrEnum):
    """MVP admits READ only. Everything else is denied unconditionally."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class PolicyRequest:
    subject: Subject
    tool_name: str
    risk_class: RiskClass
    resource: ResourceRef
    purpose: str
    investigation_id: str
    sensitivity_ceiling: Sensitivity = Sensitivity.CONFIDENTIAL
    step_seq: int = 0


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    effect: Effect
    policy_id: str
    reason: str
    binding: str
    id: str = field(default_factory=new_id)
    issued_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    obligations: tuple[str, ...] = ()

    @property
    def permitted(self) -> bool:
        return self.effect is Effect.PERMIT

    def is_expired(self, *, now: datetime | None = None) -> bool:
        return (now or datetime.now(UTC)) - self.issued_at > DECISION_TTL


def binding_for(request: PolicyRequest) -> str:
    """Hash of (subject, tool, resource, investigation).

    The gateway recomputes this from the call it is about to make and refuses a
    decision whose binding does not match - so a PERMIT for one resource can
    never authorize a call to another.
    """
    # The full resource, not just its URI. environment and sensitivity are the
    # fields env_restriction and sensitivity_ceiling decide on, so leaving them
    # out would let a PERMIT issued for a public, non-production resource
    # authorize a call against a restricted production one at the same URI.
    raw = "|".join(
        [
            request.subject.user_id,
            request.subject.tenant_id,
            request.tool_name,
            str(request.risk_class),
            request.resource.system,
            request.resource.resource_id,
            request.resource.environment,
            str(request.resource.sensitivity),
            request.investigation_id,
        ]
    )
    return hashlib.sha256(raw.encode()).hexdigest()


class PolicyDecisionPoint(ABC):
    @abstractmethod
    async def evaluate(self, request: PolicyRequest) -> PolicyDecision: ...


class StaticAllowlistPDP(PolicyDecisionPoint):
    """Phase 1 implementation. Deny by default.

    Rules, in order (SDD 8.2). Phase 4 moves these to versioned policy data.
    """

    def __init__(
        self,
        *,
        allowed_tools: frozenset[str],
        resource_prefixes: frozenset[str],
        policy_version: str = "static-v1",
    ) -> None:
        self._allowed_tools = allowed_tools
        self._resource_prefixes = resource_prefixes
        self._policy_version = policy_version

    async def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        binding = binding_for(request)

        def deny(policy_id: str, reason: str) -> PolicyDecision:
            return PolicyDecision(
                effect=Effect.DENY,
                policy_id=f"{self._policy_version}/{policy_id}",
                reason=reason,
                binding=binding,
            )

        # deny_all_writes - unconditional, not overridable by role.
        if request.risk_class is not RiskClass.READ:
            return deny(
                "deny_all_writes", f"risk_class {request.risk_class} is not permitted in MVP"
            )

        # env_restriction - no non-read verb touches production; belt and braces
        # with the rule above, since risk_class is connector-declared.
        if (
            request.resource.environment == "production"
            and request.risk_class is not RiskClass.READ
        ):
            return deny("env_restriction", "non-read action against production")

        # tool_allowlist
        if request.tool_name not in self._allowed_tools:
            return deny(
                "tool_allowlist", f"tool {request.tool_name!r} is not registered for this tenant"
            )

        # resource_scope - the pilot pipeline inventory (doc 02 section 4)
        if not any(request.resource.uri.startswith(p) for p in self._resource_prefixes):
            return deny(
                "resource_scope", f"resource {request.resource.uri!r} is outside the pilot scope"
            )

        # sensitivity_ceiling
        if exceeds_ceiling(request.resource.sensitivity, request.sensitivity_ceiling):
            return deny("sensitivity_ceiling", "resource sensitivity exceeds the request ceiling")

        return PolicyDecision(
            effect=Effect.PERMIT,
            policy_id=f"{self._policy_version}/permit_read_in_scope",
            reason="read verb, registered tool, resource in pilot scope",
            binding=binding,
            obligations=("redact:pii", "truncate:64kb"),
        )
