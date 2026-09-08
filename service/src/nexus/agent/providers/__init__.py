"""Model provider selection (NX-008)."""

from __future__ import annotations

import os

from nexus.agent.model import ModelAdapter
from nexus.agent.providers.echo import EchoModelAdapter
from nexus.config import Settings
from nexus.observability.logging import get_logger

log = get_logger(__name__)


def build_model_adapter(settings: Settings) -> ModelAdapter:
    """Return the configured adapter, falling back to the stub when unusable.

    A missing credential degrades to the echo stub rather than failing startup:
    the rest of the system - evidence collection, policy, audit - is still worth
    running without a model, and an operator gets a warning rather than a crash
    loop.
    """
    if settings.model_provider != "anthropic":
        return EchoModelAdapter()

    if not _has_credentials():
        log.warning(
            "anthropic_credentials_missing",
            detail="falling back to the echo stub; set ANTHROPIC_API_KEY to use a real model",
        )
        return EchoModelAdapter()

    from nexus.agent.providers.anthropic_provider import AnthropicModelAdapter

    log.info(
        "model_provider_selected",
        provider="anthropic",
        frontier=settings.frontier_model,
        small=settings.small_model,
    )
    return AnthropicModelAdapter(
        frontier_model=settings.frontier_model,
        small_model=settings.small_model,
        max_tokens=settings.model_max_tokens,
        timeout_s=settings.model_timeout_s,
    )


def _has_credentials() -> bool:
    """The SDK also resolves an `ant auth login` profile, so an unset env var
    does not by itself mean there is no credential."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    from pathlib import Path

    return Path.home().joinpath(".config", "anthropic").exists()
