"""Model usage metering (NX-034, NX-035).

Every model call has to be counted, or the cost-per-useful-diagnosis figure that
decides Gate 6 economics cannot be produced. Wrapping the adapter rather than
counting at each call site means a new call site cannot forget to meter.
"""

from __future__ import annotations

import time
from typing import Any

from nexus.agent.budget import BudgetTracker
from nexus.agent.model import ModelAdapter, ModelMessage, ModelResponse, ModelTier
from nexus.observability.logging import get_logger

log = get_logger(__name__)

#: Indicative USD per 1k tokens by tier, used for the cost estimate that Gate 6
#: needs. Replace with the contracted rates once D-06 is settled; the figure is
#: reported as an estimate until then.
RATE_PER_1K: dict[ModelTier, tuple[float, float]] = {
    ModelTier.SMALL: (0.0, 0.0),
    ModelTier.FRONTIER: (0.0, 0.0),
}


def estimate_cost(tier: ModelTier, tokens_in: int, tokens_out: int) -> float:
    rate_in, rate_out = RATE_PER_1K.get(tier, (0.0, 0.0))
    return (tokens_in / 1000) * rate_in + (tokens_out / 1000) * rate_out


class MeteredModelAdapter(ModelAdapter):
    """Wraps an adapter so usage lands in the budget and the telemetry."""

    def __init__(
        self, inner: ModelAdapter, budget: BudgetTracker, *, investigation_id: str
    ) -> None:
        self._inner = inner
        self._budget = budget
        self._investigation_id = investigation_id
        self.calls = 0

    async def complete(
        self, messages: list[ModelMessage], *, tier: ModelTier = ModelTier.FRONTIER
    ) -> ModelResponse:
        started = time.monotonic()
        response = await self._inner.complete(messages, tier=tier)
        self._meter(response, tier, started)
        return response

    async def complete_structured(
        self,
        messages: list[ModelMessage],
        *,
        schema: dict[str, Any],
        tier: ModelTier = ModelTier.FRONTIER,
    ) -> tuple[dict[str, Any], ModelResponse]:
        started = time.monotonic()
        payload, response = await self._inner.complete_structured(
            messages, schema=schema, tier=tier
        )
        self._meter(response, tier, started)
        return payload, response

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self._inner.embed(texts)

    def _meter(self, response: ModelResponse, tier: ModelTier, started: float) -> None:
        self.calls += 1
        self._budget.record_tokens(response.tokens_in, response.tokens_out)
        latency_ms = int((time.monotonic() - started) * 1000)
        log.info(
            "model_call",
            investigation_id=self._investigation_id,
            model_id=response.model_id,
            tier=str(tier),
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
            latency_ms=latency_ms,
            estimated_cost_usd=estimate_cost(tier, response.tokens_in, response.tokens_out),
        )
