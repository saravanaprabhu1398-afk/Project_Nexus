from __future__ import annotations

from fastapi import APIRouter

from nexus.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "disabled" if settings.disabled else "ready",
        "env": settings.env,
        "model_provider": settings.model_provider,
    }
