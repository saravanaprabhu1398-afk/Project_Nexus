"""Model failure paths (Phase 1 exit criterion 5).

The echo adapter cannot fail, so until now nothing exercised what happens when
the model is unavailable or returns something unusable. A model outage must
degrade the investigation, never crash it: the evidence was already collected
and is still worth returning.
"""

from __future__ import annotations

import pytest

from nexus.agent.metering import MeteredModelAdapter
from nexus.agent.model import ModelAdapter, ModelMessage, ModelResponse, ModelTier
from nexus.api.errors import ErrorCode, NexusError
from nexus.config import Settings
from nexus.domain.models import InvestigationStatus
from tests.conftest import make_tracker


class UnavailableModel(ModelAdapter):
    """Stands in for a provider outage."""

    async def complete(self, messages, *, tier=ModelTier.FRONTIER):
        raise NexusError(ErrorCode.MODEL_UNAVAILABLE, "provider unreachable")

    async def complete_structured(self, messages, *, schema, tier=ModelTier.FRONTIER):
        raise NexusError(ErrorCode.MODEL_UNAVAILABLE, "provider unreachable")

    async def embed(self, texts):
        raise NexusError(ErrorCode.MODEL_UNAVAILABLE, "provider unreachable")


class GarbageModel(ModelAdapter):
    """Returns a response that does not satisfy the requested schema."""

    async def complete(self, messages, *, tier=ModelTier.FRONTIER):
        return ModelResponse(text="", tokens_in=10, tokens_out=0, model_id="garbage")

    async def complete_structured(self, messages, *, schema, tier=ModelTier.FRONTIER):
        raise NexusError(ErrorCode.MODEL_OUTPUT_INVALID, "response did not match the schema")

    async def embed(self, texts):
        return []


async def _run(settings: Settings, model, registry, gateway, pdp, subject, resource):
    from nexus.agent.orchestrator import Orchestrator

    orchestrator = Orchestrator(
        settings=settings, registry=registry, gateway=gateway, pdp=pdp, model=model
    )
    return await orchestrator.run(
        subject=subject,
        investigation_id="inv-model-failure",
        intent="diagnose_job_failure",
        resource=resource,
    )


async def test_model_outage_still_returns_the_evidence(
    settings, registry, gateway, pdp, subject, resource
):
    outcome = await _run(settings, UnavailableModel(), registry, gateway, pdp, subject, resource)

    assert outcome.status is InvestigationStatus.COMPLETE
    assert len(outcome.loop.evidence) == 3
    assert outcome.observation_summary is None  # degraded, not fabricated


async def test_invalid_model_output_does_not_crash_the_investigation(
    settings, registry, gateway, pdp, subject, resource
):
    outcome = await _run(settings, GarbageModel(), registry, gateway, pdp, subject, resource)
    assert outcome.status is InvestigationStatus.COMPLETE
    assert len(outcome.loop.evidence) == 3


async def test_model_error_carries_a_closed_taxonomy_code():
    with pytest.raises(NexusError) as exc:
        await UnavailableModel().complete([ModelMessage(role="user", content="x")])
    assert exc.value.code is ErrorCode.MODEL_UNAVAILABLE
    assert exc.value.retryable is True
    assert exc.value.status_code == 503


async def test_invalid_output_is_not_retryable():
    with pytest.raises(NexusError) as exc:
        await GarbageModel().complete_structured([], schema={})
    assert exc.value.code is ErrorCode.MODEL_OUTPUT_INVALID
    assert exc.value.retryable is False


async def test_a_failing_model_is_not_metered_as_usage():
    """A call that never returned did not consume output tokens."""
    budget = make_tracker()
    metered = MeteredModelAdapter(UnavailableModel(), budget, investigation_id="inv-1")
    with pytest.raises(NexusError):
        await metered.complete([ModelMessage(role="user", content="x")])
    assert budget.snapshot()["tokens_in"] == 0
    assert budget.snapshot()["tokens_out"] == 0
    assert metered.calls == 0
