"""Core domain enums and value objects (SDD 6.1)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class InvestigationStatus(StrEnum):
    QUEUED = "queued"
    PLANNING = "planning"
    INVESTIGATING = "investigating"
    SYNTHESIZING = "synthesizing"
    COMPLETE = "complete"
    FAILED = "failed"
    ABORTED = "aborted"
    NEEDS_INPUT = "needs_input"


TERMINAL_STATUSES: frozenset[InvestigationStatus] = frozenset(
    {
        InvestigationStatus.COMPLETE,
        InvestigationStatus.FAILED,
        InvestigationStatus.ABORTED,
    }
)


class Origin(StrEnum):
    USER = "user"
    EVENT = "event"
    API = "api"


class Mode(StrEnum):
    INTERACTIVE = "interactive"
    SHADOW = "shadow"


class Sensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


_SENSITIVITY_ORDER: dict[str, int] = {
    Sensitivity.PUBLIC: 0,
    Sensitivity.INTERNAL: 1,
    Sensitivity.CONFIDENTIAL: 2,
    Sensitivity.RESTRICTED: 3,
}


def exceeds_ceiling(value: Sensitivity, ceiling: Sensitivity) -> bool:
    """True when `value` is more sensitive than the request's ceiling."""
    return _SENSITIVITY_ORDER[value] > _SENSITIVITY_ORDER[ceiling]


class Freshness(StrEnum):
    LIVE = "live"
    CACHED = "cached"
    STALE = "stale"
    UNKNOWN = "unknown"


class Integrity(StrEnum):
    VALIDATED = "validated"
    UNVALIDATED = "unvalidated"
    TRUNCATED = "truncated"
    PARTIAL = "partial"


class ConfidenceBand(StrEnum):
    """Banded, not numeric (ADR-06). Criteria are published in SDD 9.4."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ABSTAIN = "abstain"


class StepOutcome(StrEnum):
    OK = "ok"
    DENIED = "denied"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    EMPTY = "empty"
    TRUNCATED = "truncated"


#: Any outcome other than OK must surface as a missing-evidence entry (SDD 11.1).
NON_OK_OUTCOMES: frozenset[StepOutcome] = frozenset(
    o for o in StepOutcome if o is not StepOutcome.OK
)


@dataclass(frozen=True, slots=True)
class Subject:
    """The identity on whose behalf every read happens (ADR-07)."""

    user_id: str
    tenant_id: str
    roles: frozenset[str] = field(default_factory=frozenset)

    def has_role(self, role: str) -> bool:
        return role in self.roles


@dataclass(frozen=True, slots=True)
class ResourceRef:
    """A resource addressed by a tool call."""

    system: str
    resource_id: str
    environment: str = "non_production"
    sensitivity: Sensitivity = Sensitivity.INTERNAL

    @property
    def uri(self) -> str:
        return f"{self.system}:{self.resource_id}"


def new_id() -> str:
    return str(uuid.uuid4())
