"""Anthropic model adapter (NX-008).

Sits behind ModelAdapter so nothing above this file knows which provider is in
use - that is the platform-independence seam (ADR-04 applies the same idea to
connectors).

Two tiers, per SDD 9.7: extraction and classification go to a small model,
synthesis to a frontier model. Routing is configuration, not code.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic

from nexus.agent.model import ModelAdapter, ModelMessage, ModelResponse, ModelTier
from nexus.api.errors import ErrorCode, NexusError
from nexus.observability.logging import get_logger

log = get_logger(__name__)

#: Policy declines are plausible here: the agent reads production logs, and a
#: stack trace can look like security content. Rather than losing the
#: investigation, the API re-runs the request on a fallback model in the same
#: call. Costs are billed at the fallback model's own rates.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicModelAdapter(ModelAdapter):
    def __init__(
        self,
        *,
        frontier_model: str,
        small_model: str,
        max_tokens: int = 16_000,
        timeout_s: float = 120.0,
    ) -> None:
        # Zero-arg client: resolves ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or an
        # `ant auth login` profile. A key is never read into our own config, so
        # it cannot reach a log line, a prompt or the trace.
        self._client = anthropic.AsyncAnthropic(timeout=timeout_s)
        self._models = {
            ModelTier.FRONTIER: frontier_model,
            ModelTier.SMALL: small_model,
        }
        self._max_tokens = max_tokens

    def model_for(self, tier: ModelTier) -> str:
        return self._models[tier]

    async def complete(
        self, messages: list[ModelMessage], *, tier: ModelTier = ModelTier.FRONTIER
    ) -> ModelResponse:
        system, turns = _split(messages)
        response = await self._call(system, turns, tier)
        text = "".join(b.text for b in response.content if b.type == "text")
        return _to_response(response, text)

    async def complete_structured(
        self,
        messages: list[ModelMessage],
        *,
        schema: dict[str, Any],
        tier: ModelTier = ModelTier.FRONTIER,
    ) -> tuple[dict[str, Any], ModelResponse]:
        system, turns = _split(messages)
        response = await self._call(
            system,
            turns,
            tier,
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        text = "".join(b.text for b in response.content if b.type == "text")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise NexusError(
                ErrorCode.MODEL_OUTPUT_INVALID,
                f"model response was not valid JSON: {exc}",
                remediation="Tighten the schema, or fall back to an evidence-only report.",
            ) from exc
        return payload, _to_response(response, text)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Anthropic has no embeddings endpoint.

        Knowledge retrieval (Phase 3, NX-091) needs a separate embedding
        provider. Failing loudly here is deliberate: returning a plausible
        vector would produce silently meaningless similarity scores.
        """
        raise NotImplementedError(
            "AnthropicModelAdapter has no embeddings. Configure a dedicated "
            "embedding provider before enabling knowledge retrieval."
        )

    async def _call(
        self,
        system: str | None,
        turns: list[dict[str, str]],
        tier: ModelTier,
        output_config: dict[str, Any] | None = None,
    ) -> Any:
        model = self._models[tier]
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": self._max_tokens,
            "messages": turns,
        }
        if system:
            kwargs["system"] = system
        if output_config:
            kwargs["output_config"] = output_config
        if tier is ModelTier.FRONTIER:
            # Adaptive thinking on the reasoning tier; the small tier does not
            # take it and does not need it for extraction work.
            kwargs["thinking"] = {"type": "adaptive"}
            kwargs["betas"] = [FALLBACK_BETA]
            kwargs["fallbacks"] = "default"

        try:
            if tier is ModelTier.FRONTIER:
                response = await self._client.beta.messages.create(**kwargs)
            else:
                response = await self._client.messages.create(**kwargs)
        except anthropic.AuthenticationError as exc:
            raise NexusError(
                ErrorCode.MODEL_UNAVAILABLE,
                "the model provider rejected our credentials",
                remediation="Check ANTHROPIC_API_KEY, or run `ant auth login`.",
            ) from exc
        except anthropic.RateLimitError as exc:
            raise NexusError(
                ErrorCode.UPSTREAM_RATE_LIMITED,
                "the model provider is rate limiting us",
                remediation="Retry after the provider's retry-after interval.",
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise NexusError(
                ErrorCode.MODEL_UNAVAILABLE,
                f"could not reach the model provider: {exc}",
                remediation="Check network connectivity, then retry.",
            ) from exc
        except anthropic.APIStatusError as exc:
            raise NexusError(
                ErrorCode.MODEL_UNAVAILABLE
                if exc.status_code >= 500
                else ErrorCode.MODEL_OUTPUT_INVALID,
                f"model provider returned {exc.status_code}: {exc.message}",
            ) from exc

        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            raise NexusError(
                ErrorCode.MODEL_OUTPUT_INVALID,
                "the model declined this request"
                + (f" ({details.category})" if details and details.category else ""),
                remediation=(
                    "The investigation continues without a summary. If this recurs, "
                    "the evidence being sent is probably triggering a safety classifier."
                ),
            )
        if response.stop_reason == "max_tokens":
            log.warning("model_output_truncated", model=model, tier=str(tier))
        return response


def _split(messages: list[ModelMessage]) -> tuple[str | None, list[dict[str, str]]]:
    """Anthropic takes the system prompt as its own parameter, not a turn."""
    system = "\n\n".join(m.content for m in messages if m.role == "system") or None
    turns = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
    if not turns:
        raise NexusError(ErrorCode.MODEL_OUTPUT_INVALID, "no user turn was supplied to the model")
    return system, turns


def _to_response(response: Any, text: str) -> ModelResponse:
    usage = response.usage
    # Cached reads are billed differently but are still input the model saw.
    cached = (getattr(usage, "cache_read_input_tokens", 0) or 0) + (
        getattr(usage, "cache_creation_input_tokens", 0) or 0
    )
    return ModelResponse(
        text=text,
        tokens_in=usage.input_tokens + cached,
        tokens_out=usage.output_tokens,
        model_id=response.model,
    )
