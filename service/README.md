# NEXUS Agent Service - Phase 1

Core agent platform foundation for NEXUS, the read-only AI investigator for
data-platform incidents.

**Phase 1 of 6** (delivery plan Weeks 2-3). Design authority:
[`../NEXUS_Solution_Design_Document_v1.0.md`](../NEXUS_Solution_Design_Document_v1.0.md).
Backlog IDs (`NX-nnn`) and decisions (`ADR-nn`) referenced in code comments live
there and in [`../Phase_0_Package/10_Product_Backlog.md`](../Phase_0_Package/10_Product_Backlog.md).

---

## Quick start

```bash
cd service
uv sync --python 3.12
make migrate          # apply the schema; the service does not create it on boot
uv run pytest -q
make run              # migrates, then serves on :8000
```

Or the full stack on PostgreSQL and Redis, with migrations run as a separate
one-shot step before the API starts:

```bash
make up
```

Drive one investigation end to end against the mock connector:

```bash
curl -X POST http://127.0.0.1:8000/v1/investigations \
  -H 'Content-Type: application/json' \
  -H 'X-Nexus-User: eng-1' -H 'X-Nexus-Tenant: pilot-a' \
  -d '{"question":"Why did customer_daily_ingestion fail?",
       "resource_refs":[{"type":"databricks_job","id":"1234","workspace":"ws"}]}'
```

Then `GET /v1/investigations/{id}` for the result, `/evidence` for the cited
artifacts, `/audit` for the trail. Interactive docs at `/docs`.

`make check` runs lint, types, and tests. `make up` runs the stack on Postgres
and Redis via Docker.

---

## What is deliberately load-bearing

Five things are built now even though they harden later. Each is here because
retrofitting it is a migration rather than a change. **Do not remove or route
around them** without a gate decision.

| Thing | Where | Why now |
|---|---|---|
| **Tenant on every row and every query** | `db/repository.py` | Retrofitting tenancy after data exists is a migration (ADR-10). `test_no_repository_exposes_an_untenanted_query` guards the rule itself. |
| **Policy decision in the tool call path** | `governance/pdp.py`, `tools/gateway.py` | "100% of tool calls policy-checked" applies from the first Databricks call in Phase 2, not from Phase 4 (ADR-03). Phase 4 replaces the *implementation* behind this interface; the call path never changes. |
| **Append-only audit, written before the result returns** | `governance/audit.py` | An unauditable tool call must not happen. A failed audit write raises. |
| **Retention with a working purge** | `db/repository.py::RetentionPurge` | Never create a store without a delete path (ADR-11). |
| **Migrations as the only schema path** | `migrations/` | The service never creates or alters schema on boot: replicas would race, and a bad migration should fail the deploy rather than crash-loop the service. |
| **Budgets on every dimension** | `agent/budget.py` | Cost per useful diagnosis decides Gate 6. Exhaustion yields a reported partial result, never an unbounded loop. |

### Migrations (NX-030)

`make migrate` applies the schema; `make revision m="..."` autogenerates a new
one; `make migrate-down` steps back. Details in
[`migrations/README`](migrations/README).

Two guards make the chain worth trusting, both in `tests/test_migrations.py`:

* **Drift** - `test_migrations_do_not_drift_from_the_models` runs autogenerate
  against a migrated database and asserts the diff is empty. Add a column to
  `db/models.py` without a revision and this fails immediately, naming the
  column, instead of the mismatch surfacing at deploy time.
* **Rollback** - `test_upgrade_downgrade_upgrade_is_lossless` takes the schema
  to head, back to base, and forward again, then asserts tables, indexes and
  metadata all match. Rollback is rehearsed rather than assumed.

Tests build their schema by running the real migrations, not
`metadata.create_all`, so the migration is the single source of truth.

### Append-only audit needs two database roles (NX-022)

On PostgreSQL, revision 0001 grants the application role SELECT and INSERT on
`audit_record` and nothing else, so the guarantee is enforced by the database
rather than by convention in the repository layer.

**A REVOKE on its own is not a control.** PostgreSQL lets a superuser, and the
owner of a table, bypass the ACL completely: such a role updates and deletes
audit rows while `pg_class.relacl` shows the privilege withdrawn. That reads as
a working control and is not one. Two roles are therefore required:

    nexus      owns the schema and runs migrations
    nexus_app  what the service connects as; no superuser, owns nothing

Revision 0001 refuses to run if `NEXUS_DB_APP_ROLE` is a superuser or owns the
tables, rather than applying a control that would do nothing.
`deploy/postgres-init/01-app-role.sql` creates the role for local development.

`scripts/check_audit_append_only.py` verifies the guarantee against a live
database - it checks the role's standing, checks the privilege bits, and then
proves the point by attempting an update and a delete. It runs in CI, and
against the superuser configuration it fails with six distinct reasons.

SQLite has no privilege system, so this cannot be evidenced there. Gate 2
evidence has to come from PostgreSQL.

### The gateway invariant

There is exactly one way to invoke a tool, and it requires a `PolicyDecision`
with `effect=PERMIT` whose binding hash matches this exact
`(subject, tool, resource, investigation)` tuple and which has not expired.

No bypass path, no admin flag, no test hook - the tests exercise the same entry
point as production. `tests/test_gateway_invariant.py` exists to make breaking
this expensive.

Read-only is defended in four independent layers, so no single failure produces
a write:

1. no write-capable credential is issued to the runtime;
2. `ToolContract.__post_init__` refuses to construct a non-READ tool at all;
3. the registry therefore contains only READ tools;
4. the policy engine denies non-READ risk classes unconditionally, not overridable by role.

---

## Layout

```
src/nexus/
  api/            routes, schemas, closed error taxonomy, identity dependency
  agent/          model adapter, budgets, tool-calling loop, orchestrator
  domain/         enums, Subject, ResourceRef, the Evidence envelope
  db/             ORM models, tenant-scoped repositories, retention purge
  governance/     policy decision point, audit sink
  tools/          tool contract, registry, governed gateway, mock connector
  observability/  structured logging with secret scrubbing
tests/            35 tests; governance and isolation run as their own CI step
```

**The portability seam.** Connectors return `Evidence`, never provider-native
objects. No module above `tools/` may reference a provider-specific field name
(ADR-04) - this is what makes the platform-independence claim real rather than
aspirational, and Phase 2 adds a lint rule and contract test to enforce it.

---

## Phase 1 exit criteria

Gate 1 evidence. All are covered by `tests/test_api_investigations.py`.

- [x] NEXUS receives an engineering question
- [x] The service creates and maintains an investigation session
- [x] A mock tool is selected and invoked through the complete agent loop
- [x] Every request carries an audit and trace identifier
- [x] Failed model or tool calls produce controlled errors
- [x] Unit and integration tests pass
- [x] Basic latency, usage, and cost metrics are visible
- [x] Schema is versioned and reversible (NX-030)
- [ ] The service deploys repeatedly through CI/CD *(workflow written; needs a target environment)*

---

## Known gaps, in priority order

These are honest omissions, not oversights. Each maps to a backlog item.

| Gap | Item | Note |
|---|---|---|
| Real model provider | NX-008 | Only the deterministic `echo` adapter exists; token and cost metrics read zero until a real provider is wired. Blocked on D-06 (Gate 1). |
| Persistent audit sink | NX-022 | `AuditRow` and `AuditRepository` exist; the app currently wires the in-memory sink. Swap before any real connector. |
| Trace step persistence | NX-032 | `TraceStep` table exists; the loop logs but does not yet write rows. |
| Redis | NX-023 | Configured, not yet used. Session and cache land with Phase 2. |
| SSE progress stream | NX-004 | Polling works; the event stream is Phase 1 P1. |
| Enterprise identity | NX-106 | Dev headers today. The *claims contract* is final, so Phase 4 swaps the issuer only. |
| Timezone on read-back | - | SQLite drops tzinfo on `created_at`. Verified on PostgreSQL: these columns are `TIMESTAMP WITH TIME ZONE` and round-trip as `+00`, so this is local-only. |

---

## Conventions

- Code comments cite the backlog item or ADR that justifies a non-obvious
  constraint. If you change something carrying such a citation, the design
  document changes too.
- Errors come from the closed taxonomy in `api/errors.py`. Never a free-text
  code - failure metrics are dimensioned on it.
- Deterministic work (resolution, diffing, comparison) is code, not prompts
  (ADR-05). The model classifies and explains; it does not compute or look up.
- Untrusted content (logs, runbooks, tickets) passes through
  `agent.model.quarantine()` before entering a prompt (ADR-09).
