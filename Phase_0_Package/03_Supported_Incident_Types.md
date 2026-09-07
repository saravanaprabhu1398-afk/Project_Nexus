# 03 - Supported Incident Types

> **Status:** Derived analysis + pilot selection | **Owner:** Data engineering lead | **Due:** Wednesday 9 September 2026
> **Source:** Delivery plan Appendix B (representative set), analysed against MVP tool availability per the Solution Design Document

---

## 1. How to use this

The delivery plan proposes ten representative incident categories and requires Phase 0 to confirm the actual set. This document does the analysis the plan asks for: for each category it states **what evidence would prove it**, **which MVP tools produce that evidence**, and **how confidently NEXUS could reach a conclusion**. The pilot team then selects.

The `Detectability` rating is a design judgement, not a measurement, and should be treated as a hypothesis the evaluation set will test:

- **Strong** - a direct causal artifact is normally present in MVP-reachable evidence; a High confidence band is achievable.
- **Moderate** - evidence usually supports a correlation, not a proof; Medium band expected.
- **Weak** - the causal artifact lives outside MVP tool reach; the honest output is often an abstention plus a missing-evidence list.

A category rated Weak is not automatically excluded. Correctly abstaining and naming the missing evidence is a valid, valuable outcome - but a pilot loaded with Weak categories will look like a failure regardless of how well the system behaves.

## 2. Category analysis

### IC-01 Schema mismatch / incompatible schema evolution
- **Evidence signature:** `AnalysisException` / schema-mismatch exception in task output; column type or nullability delta between the failed run and the last successful run; Unity Catalog schema version change timestamped before the first failure.
- **MVP tools:** `databricks.get_task_output`, `databricks.compare_runs`, `catalog.get_schema`, `catalog.get_schema_history`.
- **Detectability:** **Strong.** Direct artifact plus independent corroboration from catalog history - satisfies the High band criteria in SDD 9.4.
- **Notes:** The flagship category. This is the failure the product mock illustrates and the one most likely to demonstrate value in Week 10.

### IC-02 Missing source file, partition, or upstream dataset
- **Evidence signature:** `FileNotFoundException` / `Path does not exist` / empty-read; upstream job's last successful run older than this run's start; lineage showing an upstream table not refreshed.
- **MVP tools:** `databricks.get_task_output`, `databricks.get_runs` (upstream job), `catalog.get_lineage`.
- **Detectability:** **Strong**, provided the upstream producer is itself a Databricks job visible in scope. Drops to Moderate when the upstream is an external system outside the tool gateway.
- **Notes:** Confirm during inventory whether the selected pipelines' upstreams are in-scope. If they are not, this category degrades.

### IC-03 Permission or authentication failure
- **Evidence signature:** `403` / `Unauthorized` / token or credential expiry in task output; unchanged job config with a changed outcome; identity or grant change outside the run record.
- **MVP tools:** `databricks.get_task_output`, `databricks.get_job_config`, `databricks.compare_runs`.
- **Detectability:** **Moderate.** NEXUS reliably identifies *that* it is a permission failure; identifying *what grant changed* usually requires IAM or workspace-audit sources outside MVP scope.
- **Notes:** A good abstention test case - the correct output names the failure class and states that the grant-change evidence is unavailable.

### IC-04 Cluster startup or capacity failure
- **Evidence signature:** Run state `INTERNAL_ERROR` with cluster event log entries; instance-pool exhaustion, quota, or spot-reclaim events; run never reaches task execution.
- **MVP tools:** `databricks.get_run`, `databricks.get_cluster_events`.
- **Detectability:** **Strong.** Cluster events are explicit and machine-readable.
- **Notes:** High-frequency, low-ambiguity. Useful for demonstrating speed but weak at demonstrating reasoning depth. Include, but do not let it dominate the evaluation set.

### IC-05 Dependency or library failure
- **Evidence signature:** `ImportError` / `NoClassDefFoundError` / version conflict in task output; library configuration delta between runs; runtime version change in job or cluster config.
- **MVP tools:** `databricks.get_task_output`, `databricks.get_job_config`, `databricks.compare_runs`.
- **Detectability:** **Strong** when the change is in the job or cluster spec. **Moderate** when the dependency drifted in an external artifact repository.

### IC-06 Data-quality validation failure
- **Evidence signature:** Explicit expectation/assertion failure in task output; row-count or null-rate delta versus prior runs; the failure is intentional rather than exceptional.
- **MVP tools:** `databricks.get_task_output`, `databricks.compare_runs`, `catalog.get_table_stats` (if available).
- **Detectability:** **Moderate.** NEXUS can identify the rule that failed and quantify the delta; determining *why* the data changed usually requires upstream investigation beyond the pipeline.
- **Notes:** Valuable because the recommended action is genuinely different from a code failure - it routes to a data producer, not an engineer.

### IC-07 Timeout or resource exhaustion
- **Evidence signature:** OOM / executor loss / job timeout; runtime substantially above the p95 for prior runs; input-volume increase; skew or shuffle indicators in task metrics.
- **MVP tools:** `databricks.get_run`, `databricks.get_task_output`, `databricks.compare_runs`, `databricks.get_cluster_events`.
- **Detectability:** **Moderate to Strong.** The symptom is unambiguous; distinguishing volume growth from code inefficiency from configuration change requires the run-comparison and volume-delta logic in SDD 9.4.

### IC-08 Configuration drift
- **Evidence signature:** Job, task, cluster, or parameter delta between the last successful and first failed run, with no code change.
- **MVP tools:** `databricks.get_job_config`, `databricks.compare_runs`.
- **Detectability:** **Strong** for detecting *what* changed. **Weak** for *who changed it and why* without workspace audit-log access.
- **Notes:** The deterministic config diff (SDD 9.4) does most of the work here; the model explains rather than discovers.

### IC-09 Unexpected data-volume increase or decrease
- **Evidence signature:** Input/output row-count or byte delta versus the prior-run baseline; runtime shift; downstream size anomaly.
- **MVP tools:** `databricks.get_run` metrics, `databricks.compare_runs`, `catalog.get_table_stats`.
- **Detectability:** **Moderate.** Often a contributing cause rather than the failure itself, and frequently surfaces as the explanation *behind* IC-07.
- **Notes:** Rarely a standalone pilot case; keep as a supporting signal.

### IC-10 Downstream table or storage write failure
- **Evidence signature:** Write/commit exception, `Delta` protocol or concurrent-write conflict, storage quota or permission error at write time; target table state.
- **MVP tools:** `databricks.get_task_output`, `catalog.get_schema`, `catalog.get_lineage`.
- **Detectability:** **Moderate to Strong** depending on whether the cause is protocol/schema (visible) or storage-account level (typically outside scope).

## 3. Summary and coverage

| ID | Category | Detectability | Primary MVP tools | Expected confidence band |
|---|---|---|---|---|
| IC-01 | Schema mismatch / evolution | Strong | task output, compare_runs, schema history | High |
| IC-02 | Missing source / upstream | Strong* | task output, upstream runs, lineage | High / Medium |
| IC-03 | Permission or auth failure | Moderate | task output, job config | Medium / Abstain |
| IC-04 | Cluster startup or capacity | Strong | run, cluster events | High |
| IC-05 | Dependency or library | Strong* | task output, job config, compare_runs | High / Medium |
| IC-06 | Data-quality validation | Moderate | task output, compare_runs, stats | Medium |
| IC-07 | Timeout / resource exhaustion | Moderate-Strong | run, task output, compare_runs, cluster events | Medium / High |
| IC-08 | Configuration drift | Strong (what) / Weak (who) | job config, compare_runs | High / Medium |
| IC-09 | Data-volume anomaly | Moderate | run metrics, compare_runs, stats | Medium |
| IC-10 | Downstream write failure | Moderate-Strong | task output, schema, lineage | Medium / High |

`*` conditional on the upstream or artifact source being in scope.

**Coverage check:** every category above is reachable with the Phase 2 Databricks and Unity Catalog toolset. **No category requires the GitHub connector** whose MVP inclusion is unresolved (finding A-3). Code-change correlation improves IC-05 and IC-08 but is not load-bearing for any category - which supports descoping it from MVP if the access path is slow.

## 4. Pilot selection

Select the categories the pilot will formally support. Recommendation: **4-6 categories**, weighted toward Strong detectability, with at least one Moderate category included deliberately to test abstention behaviour.

| ID | In pilot scope? | Expected volume on selected pipelines (90d) | Rationale |
|---|---|---|---|
| IC-01 | `<<FILL>>` | `<<FILL>>` | |
| IC-02 | `<<FILL>>` | `<<FILL>>` | |
| IC-03 | `<<FILL>>` | `<<FILL>>` | |
| IC-04 | `<<FILL>>` | `<<FILL>>` | |
| IC-05 | `<<FILL>>` | `<<FILL>>` | |
| IC-06 | `<<FILL>>` | `<<FILL>>` | |
| IC-07 | `<<FILL>>` | `<<FILL>>` | |
| IC-08 | `<<FILL>>` | `<<FILL>>` | |
| IC-09 | `<<FILL>>` | `<<FILL>>` | |
| IC-10 | `<<FILL>>` | `<<FILL>>` | |

**Additional categories observed in this domain but not in the plan's representative set:** `<<FILL: Data engineering lead | Wed 9 Sep>>`

## 5. Out-of-scope failure handling

For an incident outside the supported set, NEXUS must: identify that it is out of scope, collect and present the evidence it did gather, abstain from a root-cause claim, and route to the human escalation path. It must not stretch an unsupported incident into a supported category's explanation. This behaviour is tested explicitly in the evaluation set (see [11](11_Evaluation_Dataset_Plan.md) section on the abstention subset).
