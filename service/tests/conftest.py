from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from nexus.config import Settings
from nexus.db.session import create_all, dispose_engine, get_session, init_engine
from nexus.domain.models import ResourceRef, Subject
from nexus.governance.audit import InMemoryAuditSink
from nexus.governance.pdp import StaticAllowlistPDP
from nexus.main import build_app
from nexus.tools.gateway import ToolGateway
from nexus.tools.mock.databricks_mock import MOCK_TOOLS
from nexus.tools.registry import ToolRegistry


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        env="test",
        log_level="WARNING",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        model_provider="echo",
    )


@pytest.fixture
def subject() -> Subject:
    return Subject(user_id="eng-1", tenant_id="pilot-a", roles=frozenset({"data_engineer"}))


@pytest.fixture
def resource() -> ResourceRef:
    return ResourceRef(system="databricks", resource_id="ws/jobs/1234")


@pytest.fixture
def registry() -> ToolRegistry:
    r = ToolRegistry()
    for c in MOCK_TOOLS:
        r.register(c)
    return r


@pytest.fixture
def audit() -> InMemoryAuditSink:
    return InMemoryAuditSink()


@pytest.fixture
def pdp(registry: ToolRegistry) -> StaticAllowlistPDP:
    return StaticAllowlistPDP(
        allowed_tools=registry.names(),
        resource_prefixes=frozenset({"databricks:ws/jobs/"}),
    )


@pytest.fixture
def gateway(registry: ToolRegistry, audit: InMemoryAuditSink) -> ToolGateway:
    return ToolGateway(registry, audit)


@pytest_asyncio.fixture
async def db(settings: Settings):
    init_engine(settings.database_url)
    await create_all()
    try:
        async with get_session() as session:
            yield session
    finally:
        await dispose_engine()


@pytest_asyncio.fixture
async def client(settings: Settings):
    app = build_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            c.app = app  # type: ignore[attr-defined]
            yield c


AUTH_HEADERS = {
    "X-Nexus-User": "eng-1",
    "X-Nexus-Tenant": "pilot-a",
    "X-Nexus-Roles": "data_engineer",
}


@pytest.fixture
def auth() -> dict[str, str]:
    return dict(AUTH_HEADERS)
