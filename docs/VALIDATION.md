# Validation Guide

How to check, yourself, that what was built actually does what it claims.

> **Why this document is shaped the way it is.** Six times during development,
> something reported success while doing nothing: a PostgreSQL grant that
> applied correctly but was bypassed, a CI workflow GitHub never read, a patch
> that silently did not apply, a metering function with no call site, a missing
> file that lint passed over, and a migration guard that broke commits while
> logging "Running upgrade". Every one was caught by checking the *effect*, not
> the log line.
>
> So the steps below prefer tools that are not mine - `psql`, `sqlite3`, `curl`,
> `git` - over the service's own API, and most of them include a **negative
> check**: break it on purpose and confirm it fails. A control you have only
> ever seen succeed is a control you have not tested.

Each check states the command, what you should see, and what it would mean if
you saw something else.

---

## Prerequisites

```bash
cd service
uv sync --python 3.12
```

Anything below marked **[PG]** needs the PostgreSQL stack: `make up`, and
`make down` when finished. Anything marked **[DBX]** needs your Databricks
credentials exported.

---

# Phase 0 — Business definition

**Delivered:** 14 documents in `Phase_0_Package/`, a Solution Design Document,
and 11 architecture decision records.

**Fixed / found:** reviewing the approved proposal against the delivery plan
surfaced ten inconsistencies between them (A-1 to A-10) — including targets that
cannot both be met by a synchronous API, a policy engine scheduled after the
requirement it satisfies, and injection defence scheduled after the exposure it
defends against. Eight are resolved in the design; two need your decision.

### 0.1 The documents do not invent facts

```bash
grep -c "<<FILL:" Phase_0_Package/*.md | head -20
grep -ho "<<FILL:[^|]*" Phase_0_Package/02_Pilot_Pipeline_Inventory.md | head -5
```

**Expect:** every discovery document reports a non-zero count, and each marker
names what is missing. `10_Product_Backlog.md` should report 0 — it is derived,
not discovered.

**Why:** pipeline names, baselines and owners are things only you can supply. If
these had been filled with plausible-looking values you would have no way to
tell invention from fact.

### 0.2 Claims trace back to a source

```bash
grep -n "A-2\|A-6\|A-9" NEXUS_Solution_Design_Document_v1.0.md | head
ls docs/adr/
```

**Expect:** each finding appears with the design position taken on it, and each
ADR records consequences that are costs, not only benefits.

**Negative check:** open `docs/adr/0006-banded-confidence.md`. If it reads as
pure advocacy with no downside stated, the record is not doing its job.

---

# Phase 1 — Core agent platform

**Delivered:** a FastAPI service that accepts a question, plans, calls tools
through a governed gateway, collects cited evidence, and records an audit trail.
Plus a web UI, an Anthropic adapter, Alembic migrations, and 67 tests.

**Fixed after review:** two independent reviewers found defects that automated
checks had passed over. All verified against the code before fixing:

| Defect | Effect if unfixed |
|---|---|
| No exception handling in the background task | An investigation stuck at "investigating" forever, no failure code, indistinguishable from one still running |
| `AuditWriteFailed` is a `RuntimeError`; the loop caught only `NexusError` | One failed audit write took down the whole wave and orphaned sibling tasks that kept mutating an abandoned result |
| Budget checked per wave, not per step | A wave of independent steps could overshoot the ceiling between two checks |
| `replans` used `>` where five other dimensions used `>=` | One more replan than configured; the existing test had encoded the bug as expected behaviour |
| Steps never reached vanished silently | A truncated investigation looked exactly like a complete one |
| `missing_evidence` held in process memory | Lost on restart; a gapped investigation then reported no gaps |
| Policy obligations declared but never read | The decision log recorded that redaction happened while no redaction code existed |
| Binding hash covered only the resource URI | A permit for a public resource would authorize a call against a restricted one at the same URI |
| Model errors mapped to HTTP 500 | Classified retryable while returning a status that says otherwise |

### 1.1 The service runs and produces cited evidence

```bash
rm -f nexus.db && make migrate
make run          # leave running; use a second terminal below
```

```bash
curl -s -X POST http://127.0.0.1:8000/v1/investigations \
  -H 'Content-Type: application/json' \
  -H 'X-Nexus-User: eng-1' -H 'X-Nexus-Tenant: pilot-a' \
  -d '{"question":"Why did it fail?","resource_refs":[{"type":"databricks_job","id":"1234","workspace":"ws"}]}'
```

**Expect:** HTTP `202`, a `Location` header, and `"status":"queued"` — returned
immediately, not after the investigation finishes.

**Why:** the acknowledgement and the diagnosis have different deadlines (2s and
5min). A synchronous API cannot meet both; this proves the design is actually
asynchronous rather than merely documented as such.

Then, with the id from above:

```bash
curl -s "http://127.0.0.1:8000/v1/investigations/<ID>" \
  -H 'X-Nexus-User: eng-1' -H 'X-Nexus-Tenant: pilot-a' | python3 -m json.tool
```

**Expect:** `status: complete`, `stop_reason: plan_complete`, three evidence
items with citation keys, and non-zero `tokens_in`/`tokens_out`.

**Negative check — tokens must not be structurally zero.** They were once: the
metering function existed with no call site. If you see `"tokens_in": 0` on a
completed investigation, metering has regressed.

### 1.2 The UI shows the same thing the API does

Open <http://127.0.0.1:8000/>. Ask a question. You should see the investigation
appear, evidence expand with citation keys, and the Audit tab list one row per
tool call with `permit`.

**Why:** the UI reads the same endpoints. If the panel and the `curl` output
disagree, one of them is fabricating.

### 1.3 Tenant isolation — negative check

Create an investigation as `pilot-a` (above), then read it as a different
tenant:

```bash
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/v1/investigations/<ID>" \
  -H 'X-Nexus-User: eng-1' -H 'X-Nexus-Tenant: pilot-b'
```

**Expect:** `404`. Not `403`, not an empty `200`.

**Why:** a 404 means the row was never selected. A 403 would mean it was found
and then filtered, which leaks its existence.

Confirm at the storage layer, bypassing the API entirely:

```bash
sqlite3 nexus.db "select tenant_id, count(*) from investigation group by tenant_id;"
```

### 1.4 Read-only is structural, not configured — negative check

```bash
uv run python -c "
from nexus.governance.pdp import RiskClass
from nexus.tools.contract import ToolContract
try:
    ToolContract(name='databricks.restart_job', purpose='restart',
                 risk_class=RiskClass.EXECUTE, required_permission='jobs:run',
                 input_schema={})
    print('FAIL: a write-capable tool was constructed')
except ValueError as e:
    print('PASS:', e)
"
```

**Expect:** `PASS: tool 'databricks.restart_job' declares risk_class ... READ tools only`.

**Why:** this fails at construction, before any policy is consulted. A write tool
cannot enter the registry to be denied later — it cannot exist.

Then confirm nothing in the connector can write:

```bash
grep -nE "\.(post|put|patch|delete)\(" src/nexus/tools/databricks/*.py; echo "exit $?"
```

**Expect:** no matches. The client exposes only `get`.

### 1.5 A policy decision cannot be reused — negative check

```bash
uv run pytest tests/test_gateway_invariant.py -v 2>&1 | tail -15
```

**Expect:** all pass, including `test_decision_for_another_resource_is_refused`
and `test_decision_for_another_investigation_is_refused`.

Read `src/nexus/tools/gateway.py` and satisfy yourself there is exactly one
`invoke` path and no branch that skips `_enforce_decision`.

**Why:** the whole governance claim rests on there being no second way in.

### 1.6 Audit survives a restart

Run an investigation, then — without using the API:

```bash
sqlite3 nexus.db "select action, decision, result_status from audit_record;"
```

**Expect:** one row per tool call, `decision = permit`.

Now restart the service (`Ctrl-C`, `make run`) and read the trail again through
the API. **Expect:** the same rows.

**Why:** this lived in process memory until it was fixed. The restart is the
whole test.

### 1.7 An investigation never gets stuck — negative check

```bash
uv run pytest tests/test_model_failure.py -v 2>&1 | tail -10
```

**Expect:** passes, including that a provider outage still returns the evidence
already collected.

**Why:** any unhandled failure used to leave the row at `investigating`
permanently.

### 1.8 Budgets stop at the limit — negative check

```bash
uv run pytest tests/test_budget.py -v 2>&1 | tail -8
```

**Expect:** `test_every_dimension_stops_at_its_limit_not_one_past_it` passes.

**Why:** `replans` was one too generous, and the old test asserted the bug. If
you change `>=` back to `>` in `src/nexus/agent/budget.py:59`, this test must
fail. Try it, then change it back.

### 1.9 Redaction actually runs — negative check

```bash
uv run pytest tests/test_redaction_and_obligations.py -v 2>&1 | tail -12
```

**Expect:** all pass, including that an obligation the gateway cannot honour
raises rather than being ignored.

**Why:** every permit carried "redact PII" and "truncate" obligations that
nothing read. The decision log said redaction happened; no redaction code
existed.

---

# Phase 1 — Migrations (NX-030)

**Delivered:** Alembic, two revisions, and the schema built only by migrations —
`create_all` is gone.

**Fixed:** the initial autogenerate produced an **empty** migration because it
ran against an already-populated dev database; a placeholder URL meant the CLI
would have connected to `driver://user:pass@localhost/dbname`; the append-only
grant was never called from `upgrade()`; and the guard added later broke commits
and then blocked its own recovery advice.

### 2.1 Migrations actually commit — the check that matters most

```bash
D=$(mktemp -u /tmp/val-XXXXXX.db)
NEXUS_DATABASE_URL="sqlite+aiosqlite:///$D" uv run alembic upgrade head
sqlite3 "$D" "select version_num from alembic_version;"
sqlite3 "$D" "pragma table_info(investigation);" | grep outcome
```

**Expect:** `0002`, and an `outcome` column.

**Why:** for a while both revisions logged "Running upgrade" while committing
nothing. The log is not the evidence — the schema is.

### 2.2 Models and migrations have not drifted

```bash
uv run pytest tests/test_migrations.py -v 2>&1 | tail -12
```

**Negative check:** add a column to `src/nexus/db/models.py` without writing a
revision, re-run, and confirm `test_migrations_do_not_drift_from_the_models`
fails and names your column. Then remove it.

### 2.3 A legacy database explains itself

```bash
cp nexus.db /tmp/legacy.db
sqlite3 /tmp/legacy.db "delete from alembic_version;"
NEXUS_DATABASE_URL="sqlite+aiosqlite:////tmp/legacy.db" uv run alembic upgrade head
```

**Expect:** a readable message saying the database predates the chain, not a
hundred-line traceback.

Then confirm the recovery it recommends actually works:

```bash
NEXUS_DATABASE_URL="sqlite+aiosqlite:////tmp/legacy.db" uv run alembic stamp 0001
NEXUS_DATABASE_URL="sqlite+aiosqlite:////tmp/legacy.db" uv run alembic upgrade head
sqlite3 /tmp/legacy.db "select count(*) from investigation;"
```

**Expect:** stamp succeeds, 0002 applies, rows are preserved.

**Why:** the guard once blocked `stamp` — the error told you to run a command
the error prevented.

### 2.4 Rollback is real

```bash
D=$(mktemp -u /tmp/val2-XXXXXX.db)
NEXUS_DATABASE_URL="sqlite+aiosqlite:///$D" uv run alembic upgrade head
NEXUS_DATABASE_URL="sqlite+aiosqlite:///$D" uv run alembic downgrade base
sqlite3 "$D" ".tables"
NEXUS_DATABASE_URL="sqlite+aiosqlite:///$D" uv run alembic upgrade head
sqlite3 "$D" ".tables"
```

**Expect:** tables gone after downgrade, back after upgrade.

---

# Phase 1 — Append-only audit **[PG]**

**Delivered:** `audit_record` is insert-and-select only for the application role.

**Fixed:** the first version applied a `REVOKE` correctly — `pg_class.relacl`
showed UPDATE and DELETE withdrawn — and enforced nothing, because the service
connected as a superuser that also owned the table. Superusers bypass ACLs. It
now uses two roles, and the migration refuses to run against a superuser rather
than applying a control that would do nothing.

### 3.1 The privileges are what they claim

```bash
make up
docker compose exec -T postgres psql -U nexus -d nexus -c "
select rolname, rolsuper from pg_roles where rolname in ('nexus','nexus_app');"
docker compose exec -T postgres psql -U nexus -d nexus -c "
select has_table_privilege('nexus_app','audit_record','INSERT') as ins,
       has_table_privilege('nexus_app','audit_record','UPDATE') as upd,
       has_table_privilege('nexus_app','audit_record','DELETE') as del;"
```

**Expect:** `nexus_app` is **not** a superuser; `ins = t`, `upd = f`, `del = f`.

**Why:** the privilege bits are meaningless if the role is a superuser. Check the
role's standing first — that is exactly what was missed.

### 3.2 Prove it by trying to tamper — negative check

```bash
docker compose exec -T -e PGPASSWORD=nexus_app postgres psql -U nexus_app -h localhost -d nexus -c \
 "insert into audit_record (id,tenant_id,subject_id,occurred_at,action,resource,purpose,result_status)
  values ('v1','t','s',now(),'tool.invoke','r','validate','ok');"
docker compose exec -T -e PGPASSWORD=nexus_app postgres psql -U nexus_app -h localhost -d nexus -c \
 "update audit_record set result_status='tampered' where id='v1';"
docker compose exec -T -e PGPASSWORD=nexus_app postgres psql -U nexus_app -h localhost -d nexus -c \
 "delete from audit_record where id='v1';"
docker compose exec -T postgres psql -U nexus -d nexus -c "select id,result_status from audit_record where id='v1';"
```

**Expect:** the insert succeeds; the update and delete both fail with
`permission denied`; the row is still `ok`.

**Why:** privilege bits can be right while the write still succeeds. This is the
only check that proves it.

### 3.3 The migration refuses a vacuous configuration — negative check

```bash
docker compose run --rm -e NEXUS_DB_APP_ROLE=nexus migrate alembic upgrade head 2>&1 | tail -3
```

**Expect:** it refuses, saying the role is a superuser and the guarantee would be
vacuous.

Then restore the stack: `docker compose run --rm migrate alembic upgrade head`.

---

# Phase 2 (in progress) — Databricks connector

**Delivered:** a read-only connector, a capability probe, and a fixture
recorder. Wired to fall back to mock tools when credentials are absent.

**Found:** your workspace is serverless — zero clusters — so cluster-startup
diagnosis (IC-04) is deliberately absent rather than silently returning nothing.

### 4.1 The probe reports reality **[DBX]**

```bash
export DATABRICKS_HOST=... DATABRICKS_TOKEN=...
uv run python scripts/probe_databricks.py
```

**Expect:** a capability table. Every call is a GET; nothing is created.

**Negative check:** run it with a deliberately wrong token. It should report
authentication failure and stop, not proceed with partial results.

### 4.2 Fixtures are redacted before they touch disk **[DBX]**

```bash
uv run python scripts/record_fixtures.py
grep -riE "dapi|@[a-z]+\.(com|io)|bearer|password" tests/fixtures/ | head
```

**Expect:** the second command finds nothing. **Read the files yourself** —
redaction is a safety net, not a substitute for looking.

### 4.3 The connector reads real data **[DBX]**

```bash
export NEXUS_CONNECTOR=databricks
make migrate && make run
```

Ask about one of your real job ids in the UI.

**Expect:** evidence citing your actual runs. With no failed runs, expect it to
say so rather than inventing a diagnosis — that is correct behaviour, not a bug.

---

# Cross-cutting

### 5.1 Everything the pipeline checks

```bash
uv run ruff check src tests migrations scripts
uv run ruff format --check src tests migrations scripts
uv run mypy
uv run pytest -q
```

**Expect:** clean, and 67 tests passing.

**But:** all six defects listed at the top of this document passed these checks.
Green here means "no known regression", never "it works".

### 5.2 CI runs the same thing on a real database

```bash
gh run list --limit 3
gh run view --log | grep -E "append-only for|correctly refused a superuser"
```

**Expect:** three jobs green, and both assertions present in the log — proving
they executed rather than being skipped.

### 5.3 The read-only boundary, end to end

Enumerate every tool the service can actually register and check each one:

```bash
uv run python -c "
from nexus.tools.mock.databricks_mock import MOCK_TOOLS
from nexus.tools.databricks.client import DatabricksClient
from nexus.tools.databricks.tools import build_tools
tools = list(MOCK_TOOLS) + list(build_tools(DatabricksClient('https://x','y')))
bad = [t.name for t in tools if str(t.risk_class) != 'read']
print(f'{len(tools)} registered tools; non-READ: {bad or \"none\"}')
"
grep -rn "RiskClass\.\(WRITE\|EXECUTE\|ADMIN\)" src/nexus/; echo "(no output = none used anywhere)"
sqlite3 nexus.db "select distinct action from audit_record;"
```

**Expect:** 8 registered tools, non-READ `none`; the grep prints nothing; only
`tool.invoke` actions in the audit trail.

**Why this shape:** grepping for the string `risk_class` matches docstrings and
variable references, so a "no matches" expectation would be wrong and you would
learn to ignore it. Enumerating the actual contracts asks the real question.

---

## If a check fails

Tell me which one and paste the output. A failing check here is more useful than
a passing test suite — six of the defects above were invisible to the suite and
visible only to a direct check like these.
