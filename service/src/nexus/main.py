"""FastAPI application factory (NX-001)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from nexus.agent.orchestrator import Orchestrator
from nexus.agent.providers import build_model_adapter
from nexus.api.errors import NexusError
from nexus.api.routes import health, investigations
from nexus.config import Settings, get_settings
from nexus.db.session import dispose_engine, init_engine
from nexus.governance.audit import DatabaseAuditSink
from nexus.governance.pdp import StaticAllowlistPDP
from nexus.observability.logging import configure_logging, get_logger
from nexus.observability.trace import DatabaseTraceSink
from nexus.tools.contract import ToolContract
from nexus.tools.gateway import ToolGateway
from nexus.tools.mock.databricks_mock import MOCK_TOOLS
from nexus.tools.registry import ToolRegistry

log = get_logger(__name__)

PROMPT_VERSION = "p1-bootstrap-1"
POLICY_VERSION = "static-v1"


def _tools_for(settings: Settings) -> tuple[ToolContract, ...]:
    """Real connector when it is configured, the stub otherwise.

    A missing credential falls back rather than failing startup: the rest of the
    system is still worth running, and an operator gets a warning instead of a
    crash loop.
    """
    if settings.connector != "databricks":
        return MOCK_TOOLS

    host = os.environ.get("DATABRICKS_HOST", "")
    token = os.environ.get("DATABRICKS_TOKEN", "")
    if not host or not token:
        log.warning(
            "databricks_credentials_missing",
            detail="falling back to mock tools; set DATABRICKS_HOST and DATABRICKS_TOKEN",
        )
        return MOCK_TOOLS

    from nexus.tools.databricks.client import DatabricksClient
    from nexus.tools.databricks.tools import build_tools

    log.info("connector_selected", connector="databricks")
    return build_tools(DatabricksClient(host, token))


def build_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Schema is applied by `alembic upgrade head` as a deploy step, never
        # here: several replicas booting at once would race, and a failed
        # migration should fail the deploy rather than crash-loop the service
        # (NX-030, migrations/README).
        init_engine(settings.database_url)
        log.info("nexus_started", env=settings.env, provider=settings.model_provider)
        try:
            yield
        finally:
            await dispose_engine()
            log.info("nexus_stopped")

    app = FastAPI(
        title="NEXUS Agent API",
        version="0.1.0",
        summary="Read-only AI investigator for data-platform incidents. Phase 1.",
        lifespan=lifespan,
    )

    registry = ToolRegistry()
    for contract in _tools_for(settings):
        registry.register(contract)

    # Durable, append-only. On PostgreSQL the application role cannot alter or
    # remove a record once written (NX-022).
    audit = DatabaseAuditSink()
    trace = DatabaseTraceSink(retention_days=settings.retention_trace_days)
    pdp = StaticAllowlistPDP(
        allowed_tools=registry.names(),
        # Phase 0 doc 02 section 4 supplies the real pilot scope prefixes.
        # Doc 02 §4 supplies the real pilot scope. Until it is filled in, the
        # prefix admits the configured workspace only.
        resource_prefixes=frozenset({settings.databricks_resource_prefix}),
        policy_version=POLICY_VERSION,
    )
    gateway = ToolGateway(registry, audit)

    app.state.settings = settings
    app.state.registry = registry
    app.state.audit = audit
    app.state.trace = trace
    app.state.pdp = pdp
    app.state.prompt_version = PROMPT_VERSION
    app.state.policy_version = POLICY_VERSION
    app.state.orchestrator = Orchestrator(
        settings=settings,
        registry=registry,
        gateway=gateway,
        pdp=pdp,
        model=build_model_adapter(settings),
        trace=trace,
    )

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        """The pilot interface. Served from the same origin as the API so the
        browser needs no CORS grant and no separate build step exists."""
        return FileResponse(Path(__file__).parent / "web" / "index.html")

    app.include_router(health.router)
    app.include_router(investigations.router)

    @app.exception_handler(NexusError)
    async def _nexus_error(_request: Request, exc: NexusError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    return app


app = build_app()
