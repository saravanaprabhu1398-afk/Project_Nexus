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


async def test_migration_actually_persists(tmp_path):
    """Migrations reporting success is not the same as migrations committing.

    A check added to env.py once queried the migration connection before Alembic
    configured its transaction, which turned Alembic's begin_transaction() into
    a nested no-op: both revisions logged "Running upgrade" while the schema and
    the version row were rolled back. Nothing else caught it, because the log
    said it worked.
    """
    url = f"sqlite+aiosqlite:///{tmp_path / 'persist.db'}"
    await upgrade_to_head(url)

    def _state(connection: Connection) -> tuple[str | None, bool]:
        version = connection.exec_driver_sql("select version_num from alembic_version").scalar()
        columns = {c["name"] for c in inspect(connection).get_columns("investigation")}
        return version, "outcome" in columns

    version, has_outcome = await _inspect(url, _state)
    assert version is not None, "alembic_version is empty - nothing was committed"
    assert has_outcome, "revision 0002 did not persist its column"


async def test_a_database_predating_the_chain_is_explained_not_replayed(tmp_path):
    """The failure mode the user actually hit.

    Tables from the old create_all path with no recorded revision: Alembic
    decides the database is empty and dies on "table already exists" inside a
    hundred lines of traceback that never name the problem.
    """
    import pytest

    url = f"sqlite+aiosqlite:///{tmp_path / 'legacy.db'}"
    await upgrade_to_head(url)

    # Strip the revision, leaving the tables: exactly the legacy shape.
    def _unstamp(connection: Connection) -> None:
        connection.exec_driver_sql("delete from alembic_version")
        connection.commit()

    await _inspect(url, _unstamp)

    with pytest.raises(RuntimeError, match="predates the migration chain"):
        await upgrade_to_head(url)


async def test_stamp_is_not_blocked_by_the_guard(tmp_path):
    """The guard must not block the recovery it recommends."""
    import asyncio

    from alembic import command

    from tests.conftest import alembic_config

    url = f"sqlite+aiosqlite:///{tmp_path / 'stampable.db'}"
    await upgrade_to_head(url)

    def _unstamp(connection: Connection) -> None:
        connection.exec_driver_sql("delete from alembic_version")
        connection.commit()

    await _inspect(url, _unstamp)

    # Must not raise, and must leave the database versioned again. The CLI form
    # (`alembic stamp`) is unguarded automatically; a programmatic caller passes
    # the documented bypass, because Alembic only populates cmd_opts from argv.
    await asyncio.to_thread(command.stamp, alembic_config(url, allow_unversioned=True), "0001")
    version = await _inspect(
        url,
        lambda c: c.exec_driver_sql("select version_num from alembic_version").scalar(),
    )
    assert version == "0001"
