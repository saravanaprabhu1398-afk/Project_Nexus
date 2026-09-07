"""Migrations (NX-030).

Two things are worth testing about a migration chain, and neither is "does it
run":

  * the migrations and the ORM models must not drift apart - otherwise the
    schema a deploy builds differs from the one the code expects, and nothing
    notices until production;
  * every revision must be reversible, because a release that cannot be rolled
    back is a release that cannot safely be shipped.
"""

from __future__ import annotations

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from nexus.db.models import Base
from tests.conftest import downgrade_to, upgrade_to_head

EXPECTED_TABLES = {"investigation", "evidence", "trace_step", "audit_record"}


def _diff(connection: Connection) -> list:
    context = MigrationContext.configure(
        connection, opts={"compare_type": True, "render_as_batch": True}
    )
    return compare_metadata(context, Base.metadata)


def _tables(connection: Connection) -> set[str]:
    return set(inspect(connection).get_table_names())


def _indexes(connection: Connection, table: str) -> set[str]:
    return {i["name"] for i in inspect(connection).get_indexes(table)}


async def _inspect(url: str, fn):
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            return await conn.run_sync(fn)
    finally:
        await engine.dispose()


async def test_head_creates_every_table(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'schema.db'}"
    await upgrade_to_head(url)
    assert EXPECTED_TABLES <= await _inspect(url, _tables)


async def test_migrations_do_not_drift_from_the_models(tmp_path):
    """The guard that makes this ticket worth doing.

    If someone adds a column to db/models.py and forgets the revision, this
    fails immediately rather than at deploy time.
    """
    url = f"sqlite+aiosqlite:///{tmp_path / 'drift.db'}"
    await upgrade_to_head(url)
    diff = await _inspect(url, _diff)
    assert diff == [], f"models and migrations have drifted: {diff}"


async def test_downgrade_to_base_removes_the_schema(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'down.db'}"
    await upgrade_to_head(url)
    await downgrade_to(url, "base")
    remaining = await _inspect(url, _tables)
    assert not (EXPECTED_TABLES & remaining)


async def test_upgrade_downgrade_upgrade_is_lossless(tmp_path):
    """Rollback rehearsal: a round trip leaves the schema exactly as it was."""
    url = f"sqlite+aiosqlite:///{tmp_path / 'roundtrip.db'}"

    await upgrade_to_head(url)
    before_tables = await _inspect(url, _tables)
    before_indexes = {
        t: await _inspect(url, lambda c, t=t: _indexes(c, t)) for t in EXPECTED_TABLES
    }

    await downgrade_to(url, "base")
    await upgrade_to_head(url)

    assert await _inspect(url, _tables) == before_tables
    for table, indexes in before_indexes.items():
        assert await _inspect(url, lambda c, t=table: _indexes(c, t)) == indexes
    assert await _inspect(url, _diff) == []


async def test_tenant_id_leads_every_composite_index(tmp_path):
    """ADR-10 at the storage layer.

    A composite index that does not lead with tenant_id will not serve a
    tenant-scoped query efficiently, and its existence usually means someone
    added a query path that forgot the tenant.
    """
    url = f"sqlite+aiosqlite:///{tmp_path / 'idx.db'}"
    await upgrade_to_head(url)

    def _composite(connection: Connection) -> dict[str, list[str]]:
        found = {}
        for table in EXPECTED_TABLES:
            for index in inspect(connection).get_indexes(table):
                cols = list(index["column_names"])
                if len(cols) > 1:
                    found[index["name"]] = cols
        return found

    composites = await _inspect(url, _composite)
    assert composites, "expected composite indexes to exist"
    for name, cols in composites.items():
        assert cols[0] == "tenant_id", f"index {name} leads with {cols[0]!r}, not tenant_id"
