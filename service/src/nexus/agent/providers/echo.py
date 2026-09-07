"""Deterministic local model adapter - no network, no cost, no key.

Used by tests and local development so the full agent loop is exercisable
before any provider contract is signed (D-06 is open until Gate 1).
"""

from __future__ import annotations

import json
from typing import Any

from nexus.agent.model import ModelAdapter, ModelMessage, ModelResponse, ModelTier


def _count_tokens(text: str) -> int:
    """Crude but deterministic. Real adapters report provider token counts."""
    return max(1, len(text) // 4)


class EchoModelAdapter(ModelAdapter):
    model_id = "echo-local"

    def __init__(self, scripted: list[dict[str, Any]] | None = None) -> None:
        self._scripted = list(scripted or [])

    async def complete(
        self, messages: list[ModelMessage], *, tier: ModelTier = ModelTier.FRONTIER
    ) -> ModelResponse:
        prompt = "\n".join(m.content for m in messages)
        text = f"[echo:{tier}] {messages[-1].content[:200]}" if messages else "[echo]"
        return ModelResponse(
            text=text,
            tokens_in=_count_tokens(prompt),
            tokens_out=_count_tokens(text),
            model_id=self.model_id,
        )

    async def complete_structured(
        self,
        messages: list[ModelMessage],
        *,
        schema: dict[str, Any],
        tier: ModelTier = ModelTier.FRONTIER,
    ) -> tuple[dict[str, Any], ModelResponse]:
        payload = self._scripted.pop(0) if self._scripted else {}
        text = json.dumps(payload)
        prompt = "\n".join(m.content for m in messages)
        return payload, ModelResponse(
            text=text,
            tokens_in=_count_tokens(prompt),
            tokens_out=_count_tokens(text),
            model_id=self.model_id,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t) % 7), float(len(t) % 11), float(len(t) % 13)] for t in texts]
