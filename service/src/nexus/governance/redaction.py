"""Text redaction (NX-066, SDD 10.3 stage 2).

Applied to free text - principally log lines and stack traces, the least
governed and highest risk evidence source - before it is persisted or reaches a
model.

This is the pattern stage. The structural stage (dropping known-sensitive
connector fields) belongs with each connector in Phase 2.
"""

from __future__ import annotations

import re

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private_key",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    ),
    ("bearer_token", re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._\-]{16,}")),
    ("api_key", re.compile(r"\b(?:sk|pk|ghp|gho|xox[baprs])[-_][A-Za-z0-9_\-]{16,}")),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("url_credentials", re.compile(r"://[^\s:/@]+:[^\s:/@]+@")),
    (
        "assignment",
        re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key|credential)\b\s*[=:]\s*\S+"),
    ),
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("card", re.compile(r"\b(?:\d[ -]*?){13,19}\b")),
)

REDACTED = "[redacted]"


def redact_text(text: str) -> tuple[str, list[str]]:
    """Return the redacted text and the names of the patterns that matched.

    The pattern names are recorded on the evidence row so an auditor can see
    that redaction happened without being shown what was redacted.
    """
    applied: list[str] = []
    for name, pattern in _PATTERNS:
        replacement = "://[redacted]@" if name == "url_credentials" else REDACTED
        text, count = pattern.subn(replacement, text)
        if count:
            applied.append(f"{name}:{count}")
    return text, applied
