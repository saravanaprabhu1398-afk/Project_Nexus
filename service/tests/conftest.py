from __future__ import annotations

import asyncio
from argparse import Namespace
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

from nexus.agent.budget import Budget, BudgetTracker
from nexus.config import Settings
from nexus.db.session import dispose_engine, get_session, init_engine
from nexus.domain.models import ResourceRef, Subject
from nexus.governance.audit import InMemoryAuditSink
from nexus.governance.pdp import StaticAllowlistPDP
from nexus.main import build_app
from nexus.tools.gateway import ToolGateway
from nexus.tools.mock.databricks_mock import MOCK_TOOLS
from nexus.tools.registry import ToolRegistry

SERVICE_ROOT = Path(__file__).resolve().parents[1]


def alembic_config(database_url: str, *, allow_unversioned: bool = False) -> Config:
    cfg = Config(str(SERVICE_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(SERVICE_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    if allow_unversioned:
        # env.py reads x-arguments from cmd_opts, which only the CLI populates.
        # This is the documented bypass for a caller that knows the database
        # predates the chain - repairing it is the whole point of `stamp`.
        cfg.cmd_opts = Namespace(x=["allow_unversioned=true"])
    return cfg


async def upgrade_to_head(database_url: str) -> None:
    """Build the test schema the same way a deploy does (NX-030).

    Tests run the real migrations rather than `metadata.create_all`, so a
    migration that drifts from the models fails here instead of at deploy time.

    Alembic's env.py calls asyncio.run(), which cannot nest inside the running
    test loop - hence the thread.
    """
    await asyncio.to_thread(command.upgrade, alembic_config(database_url), "head")


async def downgrade_to(database_url: str, revision: str) -> None:
    """Step the schema back. Rollback is rehearsed, not assumed (SDD 14)."""
    await asyncio.to_thread(command.downgrade, alembic_config(database_url), revision)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        env="test",
        log_level="WARNING",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        model_provider="echo",
    )


BUDGET_DEFAULTS: dict[str, int] = {
    "wall_clock_ms": 300_000,
    "tool_calls": 25,
    "plan_steps": 15,
    "replans": 2,
    "tokens_in": 150_000,
    "tokens_out": 20_000,
}


def make_budget(**overrides: int) -> Budget:
    """Generous defaults; override one dimension to test its ceiling."""
    return Budget(**{**BUDGET_DEFAULTS, **overrides})


def make_tracker(**overrides: int) -> BudgetTracker:
    return BudgetTracker(make_budget(**overrides))


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
    await upgrade_to_head(settings.database_url)
    init_engine(settings.database_url)
    try:
        async with get_session() as session:
            yield session
    finally:
        await dispose_engine()


@pytest_asyncio.fixture
async def client(settings: Settings):
    await upgrade_to_head(settings.database_url)
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
