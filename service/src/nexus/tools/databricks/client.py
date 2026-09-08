"""Read-only Databricks REST client (NX-044).

Only GETs. There is no method here that creates, starts, cancels or modifies
anything - the read-only guarantee is enforced at four layers (SDD 4.1) and this
is the first of them: the capability simply does not exist in the code.

Errors map onto the closed taxonomy so failure metrics stay dimensionable and
the loop can tell a denial from an outage.
"""

from __future__ import annotations

from typing import Any

import httpx

from nexus.api.errors import ErrorCode, NexusError
from nexus.observability.logging import get_logger

log = get_logger(__name__)

#: Jobs 2.2 where available, 2.1 as the fallback. Serverless workspaces and
#: older trials do not all serve the same version.
JOBS_VERSIONS = ("2.2", "2.1")


class DatabricksClient:
    def __init__(self, host: str, token: str, *, timeout_s: float = 20.0) -> None:
        if not host or not token:
            raise NexusError(
                ErrorCode.AUTH_FAILED,
                "Databricks host or token is not configured",
                remediation="Set DATABRICKS_HOST and DATABRICKS_TOKEN.",
            )
        self._client = httpx.AsyncClient(
            base_url=host.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout_s,
        )
        self._jobs_version: str | None = None

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = await self._client.get(path, params=params or {})
        except httpx.TimeoutException as exc:
            raise NexusError(ErrorCode.UPSTREAM_TIMEOUT, f"Databricks timed out on {path}") from exc
        except httpx.HTTPError as exc:
            raise NexusError(
                ErrorCode.UPSTREAM_UNAVAILABLE, f"could not reach Databricks: {exc}"
            ) from exc

        if response.status_code == 200:
            body: dict[str, Any] = response.json()
            return body
        raise _map_error(response, path)

    async def jobs_get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        """Call a Jobs endpoint, pinning the API version on first success."""
        versions = (self._jobs_version,) if self._jobs_version else JOBS_VERSIONS
        last: NexusError | None = None
        for version in versions:
            try:
                body = await self.get(f"/api/{version}/jobs/{endpoint}", params)
            except NexusError as exc:
                if exc.code is not ErrorCode.RESOURCE_NOT_FOUND:
                    raise
                last = exc
                continue
            self._jobs_version = version
            return body
        raise last or NexusError(
            ErrorCode.RESOURCE_NOT_FOUND, f"no Jobs API version served /{endpoint}"
        )


def _map_error(response: httpx.Response, path: str) -> NexusError:
    detail = response.text[:200]
    if response.status_code in (401, 403):
        return NexusError(
            ErrorCode.AUTHZ_DENIED,
            f"Databricks refused access to {path}",
            remediation="The token lacks permission for this resource.",
        )
    if response.status_code == 404:
        return NexusError(ErrorCode.RESOURCE_NOT_FOUND, f"{path} not found: {detail}")
    if response.status_code == 429:
        return NexusError(ErrorCode.UPSTREAM_RATE_LIMITED, "Databricks is rate limiting us")
    if response.status_code >= 500:
        return NexusError(
            ErrorCode.UPSTREAM_UNAVAILABLE, f"Databricks {response.status_code}: {detail}"
        )
    return NexusError(
        ErrorCode.SCHEMA_VALIDATION_FAILED, f"Databricks {response.status_code}: {detail}"
    )
