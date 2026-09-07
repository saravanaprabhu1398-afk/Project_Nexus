"""Closed error taxonomy (SDD 11.2, NX-014).

Error codes are a closed set. A new failure mode gets a new member here, never
a free-text string, so that failure metrics stay dimensionable.
"""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    AUTH_FAILED = "AUTH_FAILED"
    AUTHZ_DENIED = "AUTHZ_DENIED"
    POLICY_DENIED = "POLICY_DENIED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    AMBIGUOUS_TARGET = "AMBIGUOUS_TARGET"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    UPSTREAM_RATE_LIMITED = "UPSTREAM_RATE_LIMITED"
    SCHEMA_VALIDATION_FAILED = "SCHEMA_VALIDATION_FAILED"
    OUTPUT_TOO_LARGE = "OUTPUT_TOO_LARGE"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    MODEL_OUTPUT_INVALID = "MODEL_OUTPUT_INVALID"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    SERVICE_DISABLED = "SERVICE_DISABLED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


RETRYABLE: frozenset[ErrorCode] = frozenset(
    {
        ErrorCode.UPSTREAM_TIMEOUT,
        ErrorCode.UPSTREAM_UNAVAILABLE,
        ErrorCode.UPSTREAM_RATE_LIMITED,
        ErrorCode.MODEL_UNAVAILABLE,
    }
)

_STATUS: dict[ErrorCode, int] = {
    ErrorCode.AUTH_FAILED: 401,
    ErrorCode.AUTHZ_DENIED: 403,
    ErrorCode.POLICY_DENIED: 403,
    ErrorCode.RESOURCE_NOT_FOUND: 404,
    ErrorCode.AMBIGUOUS_TARGET: 409,
    ErrorCode.SCHEMA_VALIDATION_FAILED: 422,
    ErrorCode.BUDGET_EXHAUSTED: 429,
    ErrorCode.UPSTREAM_RATE_LIMITED: 429,
    ErrorCode.SERVICE_DISABLED: 503,
    ErrorCode.UPSTREAM_UNAVAILABLE: 503,
    ErrorCode.UPSTREAM_TIMEOUT: 504,
}


class NexusError(Exception):
    """Every error crossing the API boundary carries a code and a remediation hint."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        remediation: str | None = None,
        correlation_id: str | None = None,
        partial_results_available: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.remediation = remediation
        self.correlation_id = correlation_id
        self.partial_results_available = partial_results_available

    @property
    def retryable(self) -> bool:
        return self.code in RETRYABLE

    @property
    def status_code(self) -> int:
        return _STATUS.get(self.code, 500)

    def to_payload(self) -> dict[str, object]:
        return {
            "error_code": str(self.code),
            "message": self.message,
            "remediation": self.remediation,
            "retryable": self.retryable,
            "correlation_id": self.correlation_id,
            "partial_results_available": self.partial_results_available,
        }
