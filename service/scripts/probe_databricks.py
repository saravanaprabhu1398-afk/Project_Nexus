"""Report what a Databricks workspace actually exposes (Phase 0, doc 02 §6).

Read-only: every call is a GET or a list. Nothing is created, started, or
changed. Run it against a trial workspace before building the connector, so the
evidence layer is designed around what is really there rather than what the
docs say should be.

    export DATABRICKS_HOST=https://dbc-xxxxxxxx-xxxx.cloud.databricks.com
    export DATABRICKS_TOKEN=dapi...
    uv run python scripts/probe_databricks.py

The token is read from the environment and never written anywhere.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import httpx

HOST = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
TOKEN = os.environ.get("DATABRICKS_TOKEN", "")

OK, WARN, BAD = "yes", "limited", "NO"


def probe(client: httpx.Client, path: str, params: dict[str, Any] | None = None) -> tuple[str, Any]:
    try:
        r = client.get(path, params=params or {})
    except httpx.HTTPError as exc:
        return BAD, f"{type(exc).__name__}: {exc}"
    if r.status_code == 200:
        return OK, r.json()
    if r.status_code in (401, 403):
        return BAD, f"{r.status_code} not permitted on this workspace/token"
    if r.status_code == 404:
        return BAD, f"404 endpoint not available ({path})"
    return WARN, f"{r.status_code} {r.text[:120]}"


def main() -> int:
    if not HOST or not TOKEN:
        print("Set DATABRICKS_HOST and DATABRICKS_TOKEN first.", file=sys.stderr)
        print(
            "  export DATABRICKS_HOST=https://<workspace>.cloud.databricks.com",
            file=sys.stderr,
        )
        print("  export DATABRICKS_TOKEN=dapi...", file=sys.stderr)
        return 2

    client = httpx.Client(
        base_url=HOST,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=30.0,
    )
    rows: list[tuple[str, str, str, str]] = []

    def row(capability: str, need: str, status: str, note: str) -> None:
        rows.append((capability, need, status, note[:88]))

    # --- identity ------------------------------------------------------------
    status, data = probe(client, "/api/2.0/preview/scim/v2/Me")
    who = data.get("userName", "?") if status == OK and isinstance(data, dict) else str(data)
    row("Authentication", "required", status, f"as {who}" if status == OK else str(data))
    if status != OK:
        _render(rows)
        print("\nAuthentication failed - nothing else can be probed.")
        return 1

    # --- jobs and runs: the core of the evidence layer -----------------------
    status, data = probe(client, "/api/2.2/jobs/list", {"limit": 25})
    if status != OK:
        status, data = probe(client, "/api/2.1/jobs/list", {"limit": 25})
    jobs = data.get("jobs", []) if isinstance(data, dict) else []
    row(
        "Jobs API (list)",
        "required",
        status,
        f"{len(jobs)} job(s) visible" if status == OK else str(data),
    )

    job_id = jobs[0].get("job_id") if jobs else None
    if job_id:
        s, d = probe(client, "/api/2.2/jobs/get", {"job_id": job_id})
        row("Job configuration", "required", s, "config readable" if s == OK else str(d))
    else:
        row("Job configuration", "required", WARN, "no jobs exist yet - create one to test")

    status, data = probe(client, "/api/2.2/jobs/runs/list", {"limit": 25})
    if status != OK:
        status, data = probe(client, "/api/2.1/jobs/runs/list", {"limit": 25})
    runs = data.get("runs", []) if isinstance(data, dict) else []
    failed = [
        r
        for r in runs
        if (r.get("state") or {}).get("result_state") in {"FAILED", "TIMEDOUT", "INTERNAL_ERROR"}
    ]
    row(
        "Run history",
        "required",
        status,
        f"{len(runs)} run(s), {len(failed)} failed" if status == OK else str(data),
    )

    run_id = (failed or runs or [{}])[0].get("run_id")
    if run_id:
        s, d = probe(client, "/api/2.2/jobs/runs/get", {"run_id": run_id})
        tasks = d.get("tasks", []) if isinstance(d, dict) else []
        row("Run detail / tasks", "required", s, f"{len(tasks)} task(s)" if s == OK else str(d))

        s, d = probe(client, "/api/2.2/jobs/runs/get-output", {"run_id": run_id})
        if s != OK and tasks:
            s, d = probe(
                client, "/api/2.2/jobs/runs/get-output", {"run_id": tasks[0].get("run_id")}
            )
        has_error = isinstance(d, dict) and bool(d.get("error") or d.get("logs"))
        row(
            "Task output / error",
            "REQUIRED - the primary evidence",
            s,
            ("error text present" if has_error else "reachable, but empty for this run")
            if s == OK
            else str(d),
        )
    else:
        row("Run detail / tasks", "required", WARN, "no runs yet - run a job to test")
        row("Task output / error", "REQUIRED - the primary evidence", WARN, "no runs yet")

    # --- supporting evidence -------------------------------------------------
    status, data = probe(client, "/api/2.1/unity-catalog/catalogs")
    cats = data.get("catalogs", []) if isinstance(data, dict) else []
    row(
        "Unity Catalog",
        "schema-mismatch diagnosis",
        status,
        f"{len(cats)} catalog(s)" if status == OK else str(data),
    )

    status, data = probe(client, "/api/2.0/lineage-tracking/table-lineage")
    row(
        "Lineage",
        "upstream/downstream",
        WARN if status == BAD else status,
        "not on this tier" if status == BAD else "reachable",
    )

    status, data = probe(client, "/api/2.1/clusters/list")
    if status != OK:
        status, data = probe(client, "/api/2.0/clusters/list")
    clusters = data.get("clusters", []) if isinstance(data, dict) else []
    row(
        "Clusters",
        "capacity/startup failures",
        status,
        f"{len(clusters)} cluster(s)" if status == OK else str(data),
    )

    _render(rows)
    _verdict(rows, len(failed) if runs else 0)
    return 0


def _render(rows: list[tuple[str, str, str, str]]) -> None:
    w = max(len(r[0]) for r in rows) + 2
    print(f"\n{'CAPABILITY':<{w}}{'STATUS':<10}NOTE")
    print("-" * (w + 70))
    for capability, _need, status, note in rows:
        print(f"{capability:<{w}}{status:<10}{note}")


def _verdict(rows: list[tuple[str, str, str, str]], failed_runs: int) -> None:
    blocked = [r[0] for r in rows if r[2] == BAD and "required" in r[1].lower()]
    print()
    if blocked:
        print("BLOCKED - these are required by the evidence layer:")
        for name in blocked:
            print(f"  - {name}")
        print("\nThe connector cannot produce real evidence without them.")
        return
    print("The required endpoints are reachable.")
    if failed_runs == 0:
        print(
            "No failed runs exist yet, so there is nothing to investigate.\n"
            "Create a small job that fails on purpose - a schema mismatch is the\n"
            "highest-value first case - and run it a few times."
        )
    else:
        print(f"{failed_runs} failed run(s) available to investigate.")
    print(
        "\nNext: record these responses as fixtures. A trial workspace expires;\n"
        "the recorded responses do not, and CI needs them to stay deterministic."
    )


if __name__ == "__main__":
    raise SystemExit(main())
