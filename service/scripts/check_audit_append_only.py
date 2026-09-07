"""Assert that audit_record is genuinely append-only for the service role.

Run against PostgreSQL after migrating. SQLite has no privilege system, so this
guarantee cannot be evidenced there - Gate 2 evidence has to come from
PostgreSQL (NX-022, migrations/README).

The privilege bits alone are not sufficient evidence. PostgreSQL lets a
superuser, and the owner of a table, bypass the ACL, so a role that is either
will still update and delete audit rows while pg_class.relacl shows the
privilege withdrawn. This script checks the role's standing first, then proves
the point by attempting a write.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine

OWNER_URL = os.environ["NEXUS_DATABASE_URL"]
APP_URL = os.environ.get("APP_DATABASE_URL", OWNER_URL)
APP_ROLE = os.environ.get("NEXUS_DB_APP_ROLE", "nexus_app")


async def main() -> int:
    failures: list[str] = []

    owner = create_async_engine(OWNER_URL)
    try:
        async with owner.connect() as conn:
            row = (
                await conn.execute(
                    text("select rolsuper from pg_roles where rolname = :r"),
                    {"r": APP_ROLE},
                )
            ).first()
            if row is None:
                failures.append(f"role {APP_ROLE!r} does not exist")
            elif row[0]:
                failures.append(
                    f"role {APP_ROLE!r} is a superuser; the ACL is bypassed and "
                    "the append-only guarantee is vacuous"
                )

            owners = (
                (
                    await conn.execute(
                        text("select tableowner from pg_tables where tablename = 'audit_record'")
                    )
                )
                .scalars()
                .all()
            )
            if APP_ROLE in owners:
                failures.append(f"role {APP_ROLE!r} owns audit_record; an owner bypasses the ACL")

            for privilege, expected in (
                ("INSERT", True),
                ("SELECT", True),
                ("UPDATE", False),
                ("DELETE", False),
            ):
                granted = (
                    await conn.execute(
                        text("select has_table_privilege(:r, 'audit_record', :p)"),
                        {"r": APP_ROLE, "p": privilege},
                    )
                ).scalar()
                if granted is not expected:
                    failures.append(
                        f"{privilege} on audit_record is {granted} for {APP_ROLE!r}, "
                        f"expected {expected}"
                    )
    finally:
        await owner.dispose()

    # Privilege bits can be right while the write still succeeds. Prove it.
    marker = str(uuid.uuid4())  # the id column is varchar(36)
    app = create_async_engine(APP_URL)
    try:
        async with app.begin() as conn:
            await conn.execute(
                text(
                    "insert into audit_record "
                    "(id, tenant_id, subject_id, occurred_at, action, resource, "
                    " purpose, result_status) "
                    "values (:id, 'ci', 'ci', now(), 'tool.invoke', 'ci:resource', "
                    "'append_only_check', 'ok')"
                ),
                {"id": marker},
            )

        for statement in (
            "update audit_record set result_status = 'tampered' where id = :id",
            "delete from audit_record where id = :id",
        ):
            try:
                async with app.begin() as conn:
                    await conn.execute(text(statement), {"id": marker})
            except ProgrammingError:
                pass  # expected: permission denied
            else:
                failures.append(f"the application role was able to run: {statement}")
    finally:
        await app.dispose()

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1

    print(
        f"audit_record is append-only for {APP_ROLE!r}: "
        "insert and select only, verified by attempting a write"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
