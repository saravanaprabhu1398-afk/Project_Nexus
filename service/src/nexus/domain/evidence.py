"""The Evidence envelope - the portability seam (ADR-04, SDD 6.3).

Rule enforced by test_no_provider_types_above_gateway: no module above the tool
gateway may reference a provider-specific field name. Connectors return
Evidence, never provider-native objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from nexus.domain.models import Freshness, Integrity, Sensitivity, new_id


@dataclass(slots=True)
class Evidence:
    source_system: str
    source_resource_id: str
    evidence_type: str
    collected_at: datetime
    content_summary: str
    citation_key: str
    id: str = field(default_factory=new_id)
    event_at: datetime | None = None
    freshness: Freshness = Freshness.LIVE
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    integrity: Integrity = Integrity.UNVALIDATED
    authz_context: dict[str, str] = field(default_factory=dict)
    content_ref: str | None = None
    redaction_applied: list[str] = field(default_factory=list)
    retention_class: str = "evidence"
    expires_at: datetime | None = None

    def apply_retention(self, days: int) -> None:
        """Every evidence row gets an expiry at creation (ADR-11).

        Storage is never created without a delete path.
        """
        self.expires_at = self.collected_at + timedelta(days=days)

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and datetime.now(UTC) >= self.expires_at


@dataclass(slots=True)
class MissingEvidence:
    """A non-ok step becomes a first-class output entry, never a silent omission."""

    what: str
    why: str
    source_system: str | None = None
    remediation: str | None = None
