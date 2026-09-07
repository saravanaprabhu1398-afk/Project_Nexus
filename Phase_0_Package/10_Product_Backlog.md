# 10 - Initial Prioritized Product Backlog

> **Status:** Derived from PRD user stories and the Solution Design Document phase map | **Owner:** Product owner | **Due:** Wednesday 9 September 2026

---

## 1. Conventions

- **ID:** `NX-nnn`, stable for the life of the programme
- **Phase:** the phase in which the item is *delivered*. Items marked **early** are deliberately built ahead of their hardening phase; the reason is given and traces to an SDD finding.
- **Priority:** `P0` MVP-blocking · `P1` MVP-important · `P2` desirable · `P3` post-MVP
- **Size:** S (<= 2 days) · M (3-5 days) · L (> 5 days)
- **Trace:** `US-nn` PRD user story · `SC-nn` success criterion · `A-nn` SDD finding · `ADR-nn` architecture decision

## 2. Epic map

| Epic | Name | Phase | Priority |
|---|---|---|---|
| E1 | Agent runtime and API | 1 | P0 |
| E2 | Data and infrastructure foundation | 1 | P0 |
| E3 | Observability and cost telemetry | 1 | P0 |
| E4 | Governance foundation (PDP interface, audit) | 1 → 4 | P0 |
| E5 | Databricks evidence layer | 2 | P0 |
| E6 | Governed tool gateway | 2 | P0 |
| E7 | Investigation intelligence | 3 | P0 |
| E8 | Knowledge retrieval | 3 | P1 |
| E9 | Evaluation harness | 3 | P0 |
| E10 | Enterprise security hardening | 4 | P0 |
| E11 | Product experience | 5 | P0 |
| E12 | Collaboration and pilot operations | 5 | P1 |
| E13 | Production readiness | 6 | P0 |

## 3. Backlog

### E1 - Agent runtime and API `[Phase 1]`

| ID | Item | Pri | Size | Trace |
|---|---|---|---|---|
| NX-001 | FastAPI service skeleton, config, env-based settings | P0 | S | - |
| NX-002 | `POST /v1/investigations` returning `202` within 2s | P0 | M | US-01, SC-04, ADR-01 |
| NX-003 | `GET /v1/investigations/{id}` status and partial results | P0 | S | US-01 |
| NX-004 | `GET /v1/investigations/{id}/events` SSE progress stream | P1 | M | A-6, ADR-01 |
| NX-005 | Async worker pool and investigation queue | P0 | M | ADR-01 |
| NX-006 | Investigation state machine and transitions | P0 | M | - |
| NX-007 | `ModelAdapter` interface: complete, complete_structured, embed | P0 | M | ADR-05, D-06 |
| NX-008 | Provider implementation behind the adapter | P0 | M | D-06 |
| NX-009 | Structured model I/O schemas with validation and repair | P0 | M | - |
| NX-010 | Tool registry, registration, and discovery | P0 | M | - |
| NX-011 | Tool-calling loop with deterministic stop conditions | P0 | L | SDD 9.3 |
| NX-012 | Budget manager: steps, tokens, tool calls, wall clock | P0 | M | SDD 9.6, SC-26 |
| NX-013 | Timeout, retry, and cancellation handling | P0 | M | SDD 11.3 |
| NX-014 | Closed error taxonomy and API error contract | P0 | S | SDD 11.2 |
| NX-015 | Correlation and trace ID propagation | P0 | S | US-08 |
| NX-016 | Prompt versioning: files, not literals; version on every run | P0 | S | SDD 9.7 |
| NX-017 | Health and readiness endpoints | P0 | S | - |
| NX-018 | Mock tool suite for safe local development | P0 | M | - |
| NX-019 | `POST /v1/investigations/{id}/abort` | P1 | S | - |

### E2 - Data and infrastructure foundation `[Phase 1]`

| ID | Item | Pri | Size | Trace |
|---|---|---|---|---|
| NX-020 | PostgreSQL schema: investigation, evidence, trace_step, diagnosis, feedback, audit | P0 | L | SDD 6.1 |
| NX-021 | **Tenant partitioning on every table; no un-tenanted query method in the repository layer** | P0 | M | **A-10 (early)**, ADR-10 |
| NX-022 | Append-only audit table with no UPDATE/DELETE grant to the app role | P0 | M | US-08, SC-20 |
| NX-023 | Redis for session, cache, and locks | P0 | S | - |
| NX-024 | Raw payload object store with `expires_at` | P0 | M | A-9 |
| NX-025 | Secret manager integration; no credentials in config | P0 | M | SC-19 |
| NX-026 | Vector store provisioned (not populated) | P1 | S | **A-5 (early)** |
| NX-027 | Container packaging and image build | P0 | S | - |
| NX-028 | CI/CD to dev with automated tests | P0 | M | - |
| NX-029 | Dev, test, and staging environments | P0 | M | SDD 14 |
| NX-030 | Database migration tooling and rollback | P0 | S | - |

### E3 - Observability and cost `[Phase 1]`

| ID | Item | Pri | Size | Trace |
|---|---|---|---|---|
| NX-031 | Structured logging with correlation IDs; no secrets | P0 | S | SC-19 |
| NX-032 | Distributed tracing: investigation, plan, tool call, model call | P0 | M | US-08 |
| NX-033 | Tool-call telemetry: latency, outcome, error class | P0 | S | - |
| NX-034 | Model latency and token usage metrics | P0 | S | SC-26 |
| NX-035 | **Cost-per-investigation and cost-per-useful-diagnosis metrics** | P0 | M | SC-26 (must exist from P1) |
| NX-036 | Failure categorization dashboard | P0 | M | SDD 12 |
| NX-037 | Audit-write-failure alert (must be zero) | P0 | S | SC-14 |

### E4 - Governance foundation `[Phase 1 interface → Phase 4 engine]`

| ID | Item | Pri | Size | Trace |
|---|---|---|---|---|
| NX-038 | **PDP interface + decision token in the tool call path from Phase 1** | P0 | M | **A-2 (early)**, ADR-03, SC-14 |
| NX-039 | Static deny-by-default allowlist implementation | P0 | S | A-2 |
| NX-040 | Gateway invariant: no execution path without a PERMIT decision | P0 | M | SC-14, SDD 8.3 |
| NX-041 | Policy decision logging | P0 | S | SC-14 |
| NX-042 | Kill switch interface (per-tenant and global) | P1 | S | SDD 8.4 |
| NX-043 | Dev OIDC issuer with the production claims contract | P0 | S | SDD 7 |

### E5 - Databricks evidence layer `[Phase 2]`

| ID | Item | Pri | Size | Trace |
|---|---|---|---|---|
| NX-044 | Databricks connector: auth, client, error mapping | P0 | M | - |
| NX-045 | `databricks.find_job` - resolve by ID, name, or context | P0 | M | US-01 |
| NX-046 | `databricks.get_job_config` | P0 | S | IC-08 |
| NX-047 | `databricks.get_runs` - recent run history | P0 | S | IC-02 |
| NX-048 | `databricks.get_run` - run and task-level status | P0 | M | IC-04 |
| NX-049 | `databricks.get_task_output` - failure message and output | P0 | M | IC-01,03,05,06,10 |
| NX-050 | `databricks.get_cluster_events` - execution context | P0 | M | IC-04, IC-07 |
| NX-051 | `databricks.compare_runs` - **deterministic** failed vs successful diff | P0 | L | ADR-05, IC-01,05,08,09 |
| NX-052 | `catalog.get_schema` and `catalog.get_schema_history` | P0 | M | IC-01 |
| NX-053 | `catalog.get_lineage` | P1 | M | IC-02, IC-10 |
| NX-054 | `catalog.get_table_stats` | P1 | S | IC-06, IC-09 |
| NX-055 | **Normalized `Evidence` envelope; no provider fields above the gateway** | P0 | L | ADR-04, SDD 6.3 |
| NX-056 | Citation mechanism with stable user-facing keys | P0 | M | US-02, SC-06 |
| NX-057 | Freshness and integrity marking (live/cached/stale, truncated/partial) | P0 | M | SDD 6.1 |
| NX-058 | Lint rule + contract test forbidding provider types above the gateway | P0 | S | ADR-04 |
| NX-059 | Fixture library recorded from sanitized real responses | P0 | M | SDD 13.2 |
| NX-060 | Nightly non-prod workspace drift check | P1 | S | SDD 13.2 |
| NX-061 | **Retention purge job with a passing test** | P0 | M | **A-9 (early)**, ADR-11 |
| NX-062 | `github.list_commits` / `get_commit_metadata` | P2 | M | **A-3 - conditional on Gate 1** |

### E6 - Governed tool gateway `[Phase 2]`

| ID | Item | Pri | Size | Trace |
|---|---|---|---|---|
| NX-063 | Single gateway entry point; input schema validation | P0 | M | SDD 8.3 |
| NX-064 | Read-only verb enforcement and `risk_class` on every tool contract | P0 | M | SC-15 |
| NX-065 | Resource-level authorization check per call | P0 | M | US-04, SC-16 |
| NX-066 | **Two-stage redaction: structural then pattern** | P0 | L | SC-19, SDD 10.3 |
| NX-067 | Output size caps and truncation labelling | P0 | S | SDD 11.1 |
| NX-068 | Per-connector retry, timeout, circuit breaker | P0 | M | SDD 11.3 |
| NX-069 | Standardized connector error mapping | P0 | S | SDD 11.2 |
| NX-070 | Tool-call audit logging (subject, resource, purpose, decision) | P0 | M | SC-14, US-08 |
| NX-071 | Connector health checks | P1 | S | - |

### E7 - Investigation intelligence `[Phase 3]`

| ID | Item | Pri | Size | Trace |
|---|---|---|---|---|
| NX-072 | Intent classification | P0 | M | US-01 |
| NX-073 | **Deterministic resolver** with escalation on ambiguity | P0 | L | ADR-05, SDD 9.2 |
| NX-074 | `needs_input` state and candidate disambiguation to the user | P0 | M | SDD 9.2 |
| NX-075 | Planner emitting a typed plan with dependencies | P0 | L | SDD 9.3 |
| NX-076 | Bounded parallel step execution (fan-out 4) | P0 | M | SC-01, SC-02 |
| NX-077 | Investigator loop with replan limit and stop conditions | P0 | L | SDD 9.3 |
| NX-078 | Spark/Databricks error taxonomy and classifier | P0 | L | IC-01..10 |
| NX-079 | **Deterministic** schema-change, config-change, volume-delta detection | P0 | L | ADR-05 |
| NX-080 | Timeline reconstruction across evidence types | P0 | M | US-03 |
| NX-081 | Ranked hypothesis generation with alternatives | P0 | L | US-03 |
| NX-082 | **Banded confidence with published criteria** | P0 | M | **A-7**, ADR-06, SC-10 |
| NX-083 | Abstention path when no hypothesis reaches Low | P0 | M | SC-11 |
| NX-084 | Missing-evidence tracking; every non-ok step represented | P0 | M | US-03, SDD 11.1 |
| NX-085 | Standard investigation output contract | P0 | M | US-03, US-05 |
| NX-086 | Recommended next action with risk, owner, escalation path | P0 | M | US-05 |
| NX-087 | **Evaluator guardrail: reject unbound claims before persistence** | P0 | L | SC-06, SC-09, SDD 9.5 |
| NX-088 | Code-change correlation | P2 | M | **A-3 - conditional**; until resolved, emit as missing evidence |

### E8 - Knowledge retrieval `[Phase 3]`

| ID | Item | Pri | Size | Trace |
|---|---|---|---|---|
| NX-089 | Runbook ingestion and chunking | P1 | M | D-04 |
| NX-090 | Past-incident and resolution-pattern ingestion | P1 | M | D-04 |
| NX-091 | **Pre-filtered retrieval (ACL/tenant filter before ranking, never after)** | P0 | M | SC-16, SDD 6.2 |
| NX-092 | Document-level authorization | P0 | M | US-04 |
| NX-093 | Source citation and freshness on retrieved knowledge | P0 | S | SC-06 |
| NX-094 | Source withdrawal and re-index | P1 | S | Doc 08 §8 |
| NX-095 | **Untrusted-content quarantine for logs, runbooks, tickets** | P0 | M | **A-8 (early)**, ADR-09 |

### E9 - Evaluation harness `[Phase 3, built before tuning]`

| ID | Item | Pri | Size | Trace |
|---|---|---|---|---|
| NX-096 | Golden incident dataset, 30-50 labelled cases | P0 | L | ADR-08, doc 11 |
| NX-097 | Harness: run, score, report against the golden set | P0 | L | ADR-08 |
| NX-098 | Groundedness and citation-coverage scoring | P0 | M | SC-06 |
| NX-099 | Hallucination / unsupported-claim detection | P0 | M | SC-09 |
| NX-100 | Calibration measurement by confidence band | P0 | M | SC-10 |
| NX-101 | Designed-insufficient subset for abstention scoring | P0 | M | SC-11 |
| NX-102 | Adversarial / prompt-injection corpus | P0 | M | A-8 |
| NX-103 | Consistency measurement (repeat runs) | P1 | S | SC-12 |
| NX-104 | Prompt regression suite | P0 | M | - |
| NX-105 | **Evaluation suite as a deploy gate, not a report** | P0 | M | SDD 14 |

### E10 - Enterprise security hardening `[Phase 4]`

| ID | Item | Pri | Size | Trace |
|---|---|---|---|---|
| NX-106 | Enterprise IdP integration (OIDC) | P0 | M | AC-15 |
| NX-107 | RBAC, and ABAC where required | P0 | L | US-04 |
| NX-108 | **User identity delegation to Databricks and Unity Catalog** | P0 | L | D-03, ADR-07 |
| NX-109 | Full policy engine behind the Phase 1 PDP interface | P0 | L | ADR-03 |
| NX-110 | Policy as versioned data with independent rollback | P0 | M | SDD 14 |
| NX-111 | Tool allowlists, parameter restrictions, rate limits | P0 | M | SDD 8.2 |
| NX-112 | Kill switch implementation with <=30s propagation | P0 | M | SDD 8.4 |
| NX-113 | Threat model | P0 | M | Gate 4 |
| NX-114 | Security test suite: authz matrix, isolation, leakage | P0 | L | SC-16, SC-18 |
| NX-115 | Prompt-injection test scenarios | P0 | M | SC-09 |
| NX-116 | Incident-response runbook for NEXUS itself | P0 | M | T-10 |
| NX-117 | Security and architecture review package | P0 | M | Gate 4 |

### E11 - Product experience `[Phase 5]`

| ID | Item | Pri | Size | Trace |
|---|---|---|---|---|
| NX-118 | Investigation submission and pipeline/run selection | P0 | M | US-01 |
| NX-119 | Live investigation progress view | P0 | M | SC-04 |
| NX-120 | Root-cause summary with confidence and alternatives | P0 | M | US-03 |
| NX-121 | **Evidence timeline and inspection; open the source artifact** | P0 | L | US-02 |
| NX-122 | Recommended-action panel with risk and escalation | P0 | M | US-05 |
| NX-123 | Missing-evidence and abstention presentation | P0 | M | SC-11 |
| NX-124 | Feedback and correction controls | P0 | M | US-06 |
| NX-125 | Investigation history | P1 | M | - |
| NX-126 | Shareable investigation link (authorized viewers only) | P1 | M | SC-16 |
| NX-127 | Audit trail export by incident ID | P0 | M | US-08 |

### E12 - Collaboration and pilot operations `[Phase 5]`

| ID | Item | Pri | Size | Trace |
|---|---|---|---|---|
| NX-128 | Teams or Slack notification | P1 | M | AC-18 |
| NX-129 | Jira linking / draft issue creation | P1 | M | AC-19 |
| NX-130 | **Shadow-mode job-failure webhook trigger** | P1 | M | **US-07, A-4 (early)** |
| NX-131 | Human comments and investigation ownership | P2 | S | - |
| NX-132 | Pilot-user onboarding and documentation | P0 | M | Gate 5 |
| NX-133 | Support and escalation runbook | P0 | M | Gate 5 |
| NX-134 | Operational dashboard and product analytics | P0 | M | SC-23, SC-24 |
| NX-135 | Structured feedback and weekly failed-investigation review | P0 | S | Gate 5 |

### E13 - Production readiness `[Phase 6]`

| ID | Item | Pri | Size | Trace |
|---|---|---|---|---|
| NX-136 | Load and concurrency testing | P0 | M | Gate 6 |
| NX-137 | Tool and model-provider failure drills | P0 | M | SDD 11 |
| NX-138 | Partial-evidence and degraded-mode scenarios | P0 | M | SDD 11.1 |
| NX-139 | Recovery, replay, backup, restore | P0 | M | SDD 11.4 |
| NX-140 | Monitoring, alerting, SLO instrumentation | P0 | M | SDD 14 |
| NX-141 | Rollback rehearsal: image, prompt, and policy independently | P0 | M | ADR-03, SDD 14 |
| NX-142 | Cost model and updated ROI | P0 | M | SC-27, SC-28 |
| NX-143 | Production deployment architecture and operating model | P0 | M | Gate 6 |
| NX-144 | Pilot-results report and go/no-go recommendation | P0 | M | Gate 6 |
| NX-145 | Known-limitations register and post-MVP backlog | P0 | S | Gate 6 |

## 4. Post-MVP placeholders (not scheduled)

`NX-2xx` Phase 7 assisted remediation · `NX-3xx` Phase 8 event-driven response · `NX-4xx` Phase 9 governed execution · `NX-5xx` Phase 10 multi-platform. Each requires its own governance gate before entering this backlog.

## 5. Definition of done

Per the delivery plan's global definition, no item is complete until it is functional, evidence-backed, authorized, policy-controlled, tested, observable, resilient, documented, deployable, and accepted. "The agent produced an answer" is not done.

## 6. Sequencing notes

The five items most likely to be deferred under pressure, and the reason each must not be:

| Item | Why it cannot slip |
|---|---|
| NX-021 tenant partitioning | Retrofitting tenancy after data exists is a migration, not a change |
| NX-038 PDP interface in Phase 1 | Without it, "100% policy-checked" is false for all of Phase 2 |
| NX-061 retention purge job | Storage without a delete path is irreversible |
| NX-096/097 evaluation harness | Gate 3 has no evidence without it, and tuning without it overfits |
| NX-095 content quarantine | Phase 3 ingests the injection surface; the defence must precede the exposure |
