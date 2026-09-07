"""Request identity (NX-043).

Phase 1 accepts a development issuer. The *claims contract* below is the one
Phase 4 binds to the enterprise IdP - only the issuer changes, so no call site
is rewritten at Gate 4.
"""

from __future__ import annotations

from fastapi import Header

from nexus.api.errors import ErrorCode, NexusError
from nexus.domain.models import Subject


async def current_subject(
    x_nexus_user: str | None = Header(default=None),
    x_nexus_tenant: str | None = Header(default=None),
    x_nexus_roles: str | None = Header(default=None),
) -> Subject:
    if not x_nexus_user or not x_nexus_tenant:
        raise NexusError(
            ErrorCode.AUTH_FAILED,
            "no authenticated subject on the request",
            remediation=(
                "Send X-Nexus-User and X-Nexus-Tenant in development, or a bearer "
                "token from the enterprise IdP once Phase 4 identity is enabled."
            ),
        )
    roles = frozenset(r.strip() for r in (x_nexus_roles or "").split(",") if r.strip())
    return Subject(user_id=x_nexus_user, tenant_id=x_nexus_tenant, roles=roles)
