# 02 - Pilot Pipeline Inventory

> **Status:** Discovery instrument | **Owner:** Data engineering lead | **Due:** Wednesday 9 September 2026
> **Target:** 3-5 selected pipelines (delivery plan, Phase 0)

---

## 1. Why this document decides more than it appears to

Pipeline selection determines whether NEXUS can be evaluated at all. A pipeline that fails rarely produces no pilot signal. A pipeline whose logs expire in 24 hours produces no evidence. A pipeline whose owner will not grant catalog access produces no lineage. **The selection criteria below are therefore gating, not advisory** - a candidate that fails an evidence criterion should be rejected even if it is business-critical, because the pilot cannot demonstrate anything on it.

Where a criterion cannot be met, the correct response is to record it in the RAID log and select a different pipeline, not to proceed and discover the gap in Phase 2.

## 2. Selection criteria

| # | Criterion | Threshold | Why |
|---|---|---|---|
| C1 | Failure frequency | >= 2 qualifying failures/month over the last 90 days | Below this, the pilot window yields no observations |
| C2 | Run history depth | >= 30 runs retained, including successful runs | Failed-vs-successful comparison is a core Phase 2 capability |
| C3 | Log/task-output availability | Retained >= 14 days and retrievable via API | The primary evidence source |
| C4 | Unity Catalog coverage | Tables registered; schema history available | Schema-change detection is the highest-value incident class |
| C5 | Lineage availability | Upstream/downstream visible where relevant | Needed for impact and upstream-cause reasoning |
| C6 | Named system owner | Identified and reachable | Access approval and evidence questions |
| C7 | Runbook exists | Any documented operational guidance | Phase 3 knowledge retrieval has something to retrieve |
| C8 | Sensitivity approvable | Security can approve read access within Week 2 | Otherwise it blocks Phase 2 |
| C9 | Failure-mode variety | Across the selected set, >= 4 distinct incident types from [03](03_Supported_Incident_Types.md) | Avoids overfitting to one error signature |
| C10 | Operational meaning | A delay in this pipeline has articulable business impact | Needed for the value model |

C9 applies to the **set**, not to each pipeline. The others apply per pipeline.

## 3. Candidate inventory

Complete one row per candidate. Include rejected candidates - the rejection reason is itself a Gate 0 finding.

| ID | Pipeline / job name | Databricks job ID | Workspace | Business criticality | System owner | Schedule | Failures (90d) | Runs retained | Log retention | UC coverage | Lineage | Runbook | Sensitivity | Selected | Rationale / rejection reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P-01 | `<<FILL>>` | | | | | | | | | | | | | | |
| P-02 | `<<FILL>>` | | | | | | | | | | | | | | |
| P-03 | `<<FILL>>` | | | | | | | | | | | | | | |
| P-04 | `<<FILL>>` | | | | | | | | | | | | | | |
| P-05 | `<<FILL>>` | | | | | | | | | | | | | | |
| P-06 | `<<FILL>>` | | | | | | | | | | | | | | |
| P-07 | `<<FILL>>` | | | | | | | | | | | | | | |

`<<FILL: complete candidate inventory | Data engineering lead | Wed 9 Sep>>`

**Legend for evidence columns:** `Y` available and API-retrievable · `P` partial, note the gap · `N` unavailable.

## 4. Selected set summary

To be completed after selection. This table becomes the authoritative scope reference for the policy engine's `resource_scope` rule (SDD 8.2) - the agent may not read outside it.

| ID | Pipeline | Job ID | Owner | Primary incident types expected | Evidence gaps accepted |
|---|---|---|---|---|---|
| | | | | | |

**Resource scope glob for policy configuration:** `<<FILL: e.g. workspace/1234/jobs/{id list} | Technical architect | Fri 11 Sep>>`

## 5. Per-pipeline evidence profile

Complete one block per **selected** pipeline. This is the input to Phase 2 connector work and tells the team what the agent will and will not be able to see.

```
Pipeline:                 <<FILL>>
Job ID / workspace:       <<FILL>>
Task graph:               <<FILL: number of tasks, names, dependency shape>>
Compute:                  <<FILL: job cluster / all-purpose / serverless; instance profile>>
Source datasets:          <<FILL: upstream tables, files, or streams>>
Target datasets:          <<FILL: written tables>>
Downstream consumers:     <<FILL: who breaks when this breaks>>
Typical runtime:          <<FILL: p50 / p95>>
Log destination:          <<FILL: driver logs, task output, external sink>>
Log retention:            <<FILL: days>>
Catalog registration:     <<FILL: catalog.schema, schema history available Y/N>>
Data classification:      <<FILL: per document 08>>
Known recurring failures: <<FILL: describe>>
Owner (system):           <<FILL>>
Owner (data):             <<FILL>>
```

## 6. Historical incident availability

Phase 3's evaluation set (see [11](11_Evaluation_Dataset_Plan.md)) draws from these pipelines. Confirm now that history exists, because it cannot be created later.

| Question | Answer |
|---|---|
| How far back are failed runs retrievable via API? | `<<FILL>>` |
| Are the corresponding logs still retained for those runs? | `<<FILL>>` |
| Are past incidents recorded anywhere (tickets, channels, postmortems)? | `<<FILL>>` |
| Is the actual root cause recorded, or only the resolution? | `<<FILL>>` |
| Approximate number of resolvable historical incidents across the selected set | `<<FILL: need 30-50 for the golden set>>` |

**If fewer than 30 labellable historical incidents exist across the selected pipelines, escalate at Gate 0.** The options are: widen the pipeline set, extend the labelling window into Phase 1-2, or accept a smaller evaluation set with explicitly weaker Gate 3 confidence.

## 7. Sign-off

| Role | Name | Confirms | Date |
|---|---|---|---|
| Data engineering lead | | Inventory complete and accurate | |
| System owner(s) | | Pipelines may be read by NEXUS | |
| Security and privacy | | Sensitivity classification acceptable | |
| Product lead | | Selection meets pilot criteria | |
