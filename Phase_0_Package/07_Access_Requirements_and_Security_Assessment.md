# 07 - Access Requirements and Initial Security Assessment

> **Status:** Derived requirement set + approval instrument | **Owner:** Security engineer (with Integration lead) | **Due:** Thursday 10 September 2026
> **Critical path:** access approval is the longest-lead item in the programme. Submit requests Monday, not when Phase 2 begins.

---

## 1. Access principles

1. **Read-only, without exception.** No write, execute, restart, deploy, or administrative scope is requested. If a scope grants writes as a side effect, it is rejected and a narrower one is found.
2. **User delegation preferred** (SDD 10.1, decision D-03). NEXUS acts with the invoking user's effective permissions wherever the platform supports it, so the agent can never surface data the user could not have retrieved alone.
3. **Service identity is the exception, not the default**, and where used its read scope must be *narrower* than the union of pilot users' scopes.
4. **Resource-scoped, not workspace-wide.** Access is restricted to the pipelines listed in [02](02_Pilot_Pipeline_Inventory.md).
5. **Time-boxed.** All grants expire at pilot end and require renewal.
6. **Every access is audited** with subject, resource, purpose, and policy decision (SDD 6.1).

## 2. Required access by phase

### Phase 1 (Weeks 2-3) - no external data access

| Resource | Scope | Owner | Justification |
|---|---|---|---|
| Dev/test cloud subscription | Deploy agent service, Postgres, Redis, vector store, telemetry | Platform | Runtime |
| Secret manager | Read app secrets | Platform/Security | No credentials in config |
| Container registry | Push/pull | Platform | CI/CD |
| CI/CD system | Pipeline execution | Platform | Automated deployment |
| Model provider endpoint | Inference, dev quota | Architect | Model calls |

No production or customer data is reachable in Phase 1. Development uses mock tools and fixtures.

### Phase 2 (Weeks 4-5) - Databricks evidence layer

| ID | Resource | Required scope | Verbs | Owner | Identity model | Status |
|---|---|---|---|---|---|---|
| AC-01 | Databricks Jobs API | Selected job IDs only | `list`, `get` | Workspace admin | Delegated | `<<FILL>>` |
| AC-02 | Databricks Runs API | Runs of selected jobs | `list`, `get`, `get_output` | Workspace admin | Delegated | `<<FILL>>` |
| AC-03 | Task output / driver logs | Selected jobs | `read` | Workspace admin | Delegated | `<<FILL>>` |
| AC-04 | Cluster events | Clusters used by selected jobs | `list`, `get` | Workspace admin | Delegated | `<<FILL>>` |
| AC-05 | Job / cluster configuration | Selected jobs | `get` | Workspace admin | Delegated | `<<FILL>>` |
| AC-06 | Unity Catalog metadata | Catalogs/schemas of selected pipelines | `read metadata` | UC governance owner | Delegated | `<<FILL>>` |
| AC-07 | Unity Catalog schema history | As above | `read` | UC governance owner | Delegated | `<<FILL>>` |
| AC-08 | Unity Catalog lineage | As above | `read` | UC governance owner | Delegated | `<<FILL>>` |
| AC-09 | Table statistics (row counts, sizes) | As above | `read metadata` | UC governance owner | Delegated | `<<FILL>>` |
| AC-10 | Non-production Databricks workspace | Full read for testing | `read` | Workspace admin | Service | `<<FILL>>` |

**Explicitly not requested:** job start/cancel/reset, cluster create/terminate/restart, workspace file write, notebook execution, secret scope write, permission management, table data reads (metadata only unless a specific evidence need is approved separately).

> **Note on AC-06 to AC-09:** these are *metadata* reads. NEXUS does not query table contents in the MVP. If an incident category later requires sampling data values, that is a new access request with its own approval, not an extension of these grants.

### Phase 3 (Weeks 6-7) - knowledge sources

| ID | Resource | Scope | Owner | Status |
|---|---|---|---|---|
| AC-11 | Runbook repository / wiki | Pilot team's operational docs only | Doc owner | `<<FILL>>` |
| AC-12 | Historical incident records | Tickets for selected pipelines | ITSM owner | `<<FILL>>` |
| AC-13 | Architecture documentation | Pilot domain | Architecture | `<<FILL>>` |
| AC-14 | **Conditional (finding A-3):** GitHub/GitLab repository metadata | Commit and PR *metadata* for pilot pipeline repos; no source content in MVP | Repo owner | `<<FILL: pending A-3 decision at Gate 1>>` |

AC-14 exists only if Gate 1 resolves finding A-3 in favour of including code correlation. Document 03 confirms that no supported incident category depends on it, so it can be dropped without descoping the pilot.

### Phase 4 (Weeks 8-9) - enterprise identity

| ID | Resource | Scope | Owner | Status |
|---|---|---|---|---|
| AC-15 | Enterprise IdP (OIDC) app registration | Authenticate pilot users | IAM team | `<<FILL>>` |
| AC-16 | Group/role claims | Map roles to NEXUS permissions | IAM team | `<<FILL>>` |
| AC-17 | Audit log sink | Write NEXUS audit records | Security | `<<FILL>>` |

### Phase 5 (Weeks 10-11) - pilot operations

| ID | Resource | Scope | Owner | Status |
|---|---|---|---|---|
| AC-18 | Teams/Slack app registration | Notify pilot channel | Collaboration admin | `<<FILL>>` |
| AC-19 | Jira project | Read + create linked issues (drafts only) | Jira admin | `<<FILL>>` |
| AC-20 | **Pilot** Databricks workspace, read-only | Selected production pipelines | Workspace admin + system owners | `<<FILL>>` |

AC-20 is the first grant touching production data and carries the heaviest approval. It should be requested in Week 1 with a Week 9 activation date, so the approval clock runs in parallel with the build.

## 3. Access request status tracker

| ID | Requested | Approver | Submitted | Approved | Expires | Blocker |
|---|---|---|---|---|---|---|
| AC-01..AC-05 | Databricks read | `<<FILL>>` | | | Pilot end | |
| AC-06..AC-09 | Unity Catalog read | `<<FILL>>` | | | Pilot end | |
| AC-10 | Non-prod workspace | `<<FILL>>` | | | Pilot end | |
| AC-11..AC-13 | Knowledge sources | `<<FILL>>` | | | Pilot end | |
| AC-14 | Repo metadata (conditional) | `<<FILL>>` | | | Pilot end | |
| AC-15..AC-17 | Identity + audit | `<<FILL>>` | | | Pilot end | |
| AC-18..AC-19 | Collaboration | `<<FILL>>` | | | Pilot end | |
| AC-20 | **Production read** | `<<FILL>>` | | | Pilot end | |

Any grant not approved by its phase start becomes an issue in [12](12_RAID_Log.md), not a silent delay.

## 4. Initial security assessment

### 4.1 Assets and exposure

| Asset | Sensitivity | Exposure introduced by NEXUS |
|---|---|---|
| Pipeline operational metadata | Internal | Aggregated into one queryable surface |
| Log and task output | **Variable - may contain PII or secrets** | Read into the agent runtime and, after redaction, into model context |
| Catalog metadata and lineage | Internal/Confidential | Reveals data topology in one place |
| Runbooks | Internal | Indexed and retrievable |
| Investigation traces | Internal | New data class created by the product |
| Provider credentials | **Restricted** | Held by the runtime |

**The highest-risk item is log content.** Logs are the least-governed data source in most platforms, are the most likely to contain secrets or personal data by accident, and are simultaneously the primary evidence source. Redaction (SDD 10.3) is therefore a Phase 2 gating control, not a Phase 4 refinement.

### 4.2 Threat questions for Week 1

| # | Question | Answer |
|---|---|---|
| T-01 | Can any requested scope be escalated to a write? | `<<FILL>>` |
| T-02 | What prevents the agent reading outside the pilot resource scope? | Policy `resource_scope` rule + delegated identity (SDD 8.2) |
| T-03 | What stops a user seeing another user's investigation? | Tenant partitioning + per-resource authz (SDD 10.6) |
| T-04 | Can log content reach the model provider unredacted? | `<<FILL: verify redaction design accepted>>` |
| T-05 | Where is data processed and stored, and is that compliant? | `<<FILL: D-02>>` |
| T-06 | What are the model provider's data-use and retention terms? | `<<FILL: D-06>>` |
| T-07 | What happens if the agent is prompt-injected via a log line or runbook? | Quarantine + capability floor (SDD 10.5) |
| T-08 | Who can invoke the kill switch and how fast does it propagate? | Security, SRE on-call, Product owner; <= 30s (SDD 8.4) |
| T-09 | How is an unauthorized access attempt detected? | Policy denial metrics + audit alerting (SDD 12) |
| T-10 | What is the incident response if NEXUS leaks data? | `<<FILL: runbook due Phase 4>>` |

### 4.3 Controls required before each gate

| Gate | Control required |
|---|---|
| Gate 1 | Secrets never in config or logs; audit sink operational; PDP interface in the call path |
| Gate 2 | Read-only enforced at credential + contract + gateway + policy; redaction operating on log content; retention purge job working; every tool call audited |
| Gate 3 | Untrusted-content quarantine; output scanning; adversarial cases in the evaluation set |
| Gate 4 | Enterprise identity; full policy engine; threat model; isolation and injection test suites passing; formal security approval |
| Gate 5 | Production read access active with monitoring; kill switch rehearsed |
| Gate 6 | No unresolved critical or high findings; incident-response runbook tested |

### 4.4 Findings from initial review

| ID | Finding | Severity | Owner | Response | Due |
|---|---|---|---|---|---|
| SF-01 | `<<FILL>>` | | | | |

## 5. Sign-off

| Role | Name | Confirms | Date |
|---|---|---|---|
| Security engineer | | Access set is minimal and read-only | |
| Data privacy / compliance | | Data handling acceptable for pilot | |
| Databricks workspace admin | | Scopes are grantable as specified | |
| Unity Catalog owner | | Metadata access acceptable | |
| Technical architect | | Sufficient for the designed capability | |
