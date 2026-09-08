"""Record real Databricks responses as test fixtures (SDD 13.2).

A trial workspace expires. The recorded responses do not, and CI needs them to
stay deterministic and offline. Run this while the workspace is alive.

    export DATABRICKS_HOST=... DATABRICKS_TOKEN=...
    uv run python scripts/record_fixtures.py

Read-only. Every response passes through redaction before it touches disk:
emails, tokens, and workspace URLs are removed, and the file is printed so you
can see what was kept.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from nexus.governance.redaction import redact_text
from nexus.tools.databricks.client import DatabricksClient

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "databricks"
HOST = os.environ.get("DATABRICKS_HOST", "")
TOKEN = os.environ.get("DATABRICKS_TOKEN", "")

#: Workspace-identifying strings that would otherwise land in a committed file.
_HOST_RE = re.compile(r"https?://[A-Za-z0-9.\-]*(databricks|azuredatabricks)[A-Za-z0-9.\-/]*")


def sanitize(value: Any) -> Any:
    """Redact recursively. Fixtures are committed, so this runs on everything."""
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        cleaned, _ = redact_text(value)
        return _HOST_RE.sub("https://workspace.example.com", cleaned)
    return value


def write(name: str, payload: Any) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(sanitize(payload), indent=2, sort_keys=True) + "\n")
    print(f"  wrote {path.relative_to(OUT.parents[2])}  ({path.stat().st_size:,} bytes)")


async def main() -> int:
    if not HOST or not TOKEN:
        print("Set DATABRICKS_HOST and DATABRICKS_TOKEN first.", file=sys.stderr)
        return 2

    client = DatabricksClient(HOST, TOKEN)
    try:
        print("Recording from the live workspace...")
        jobs = await client.jobs_get("list", {"limit": 25})
        write("jobs_list", jobs)

        job_list = jobs.get("jobs", [])
        if not job_list:
            print("\nNo jobs in this workspace - nothing further to record.")
            return 1

        job_id = job_list[0]["job_id"]
        write("job_get", await client.jobs_get("get", {"job_id": job_id}))

        runs = await client.jobs_get("runs/list", {"job_id": job_id, "limit": 25})
        write("runs_list", runs)

        run_list = runs.get("runs", [])
        failed = [
            r
            for r in run_list
            if (r.get("state") or {}).get("result_state")
            in {"FAILED", "TIMEDOUT", "INTERNAL_ERROR"}
        ]
        target = (failed or run_list)[0] if run_list else None
        if target:
            detail = await client.jobs_get("runs/get", {"run_id": target["run_id"]})
            write("run_get_failed" if failed else "run_get_success", detail)
            for task in detail.get("tasks", []) or [{"run_id": target["run_id"]}]:
                try:
                    out = await client.jobs_get("runs/get-output", {"run_id": task.get("run_id")})
                except Exception as exc:  # noqa: BLE001
                    print(f"  (no output for task {task.get('task_key')}: {exc})")
                    continue
                write(
                    f"run_output_{task.get('task_key', 'task')}",
                    out,
                )

        try:
            catalogs = await client.get("/api/2.1/unity-catalog/catalogs")
            write("catalogs", catalogs)
            first = (catalogs.get("catalogs") or [{}])[0].get("name")
            if first:
                schemas = await client.get(
                    "/api/2.1/unity-catalog/schemas", {"catalog_name": first}
                )
                write("schemas", schemas)
                schema = (schemas.get("schemas") or [{}])[0].get("name")
                if schema:
                    tables = await client.get(
                        "/api/2.1/unity-catalog/tables",
                        {"catalog_name": first, "schema_name": schema},
                    )
                    write("tables", tables)
        except Exception as exc:  # noqa: BLE001
            print(f"  (Unity Catalog not recorded: {exc})")
    finally:
        await client.aclose()

    print(
        f"\nFixtures in {OUT}."
        "\nReview them before committing - redaction is a safety net, not a"
        "\nsubstitute for looking at what your own workspace returned."
    )
    if not failed:
        print(
            "\nNo failed run was available, so no failure fixture was recorded."
            "\nThat is the one case the product exists for - worth getting."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
