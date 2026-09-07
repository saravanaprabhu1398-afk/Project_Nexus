# 06 - Baseline Metrics Workbook

> **Status:** Discovery instrument | **Owner:** Operations lead (with Product lead) | **Due:** Thursday 10 September 2026

---

## 1. Why this is a gating deliverable

Every headline target in the proposal is expressed as a *change* - "50% reduction in median triage time", "faster diagnosis", "fewer escalations". None of them can be evaluated at Gate 6 without a number recorded now. **A baseline collected after the pilot has started is not a baseline.**

Where telemetry does not exist, do not skip the metric. Use the sampling protocol in section 4 and record the resulting number as an estimate with its method and confidence stated. An honest estimate with a stated method is decision-grade; an absent number is not.

## 2. Baseline metric set

Measurement window: **the last 90 days**, restricted to the selected pilot pipelines ([02](02_Pilot_Pipeline_Inventory.md)) and supported incident types ([03](03_Supported_Incident_Types.md)).

### 2.1 Speed

| ID | Metric | Definition | Source | Value | Method | Confidence |
|---|---|---|---|---|---|---|
| B-01 | Median time to diagnosis | Failure timestamp → root cause identified | Tickets / interviews | `<<FILL>>` | | |
| B-02 | Mean time to diagnosis | As above, mean | Tickets / interviews | `<<FILL>>` | | |
| B-03 | p90 time to diagnosis | Tail behaviour | Tickets / interviews | `<<FILL>>` | | |
| B-04 | Median time to resolution | Failure → verified resolved | Tickets | `<<FILL>>` | | |
| B-05 | Detection lag | Failure → someone knows | Job history vs. ticket | `<<FILL>>` | | |
| B-06 | Routing lag | Detection → owner engaged | Tickets / channel | `<<FILL>>` | | |
| B-07 | Evidence-collection time | Owner engaged → evidence assembled | Interviews (05) | `<<FILL>>` | | |

B-07 is the metric NEXUS most directly attacks. If it is not separable from B-01 in the available data, derive it from the incident walkthroughs in [05](05_Current_State_Incident_Workflow.md) and say so.

### 2.2 Effort

| ID | Metric | Definition | Source | Value |
|---|---|---|---|---|
| B-08 | Engineer-minutes per incident (active) | Hands-on time, all participants | Interviews / sampling | `<<FILL>>` |
| B-09 | People involved per incident | Distinct humans touching it | Tickets / channel | `<<FILL>>` |
| B-10 | Senior-engineer involvement rate | % of incidents pulling in a senior specialist | Interviews | `<<FILL>>` |
| B-11 | Escalation rate | % escalated beyond first responder | Tickets | `<<FILL>>` |
| B-12 | Interruption cost | Context switches caused per incident | Interviews | `<<FILL>>` |

### 2.3 Volume and recurrence

| ID | Metric | Definition | Source | Value |
|---|---|---|---|---|
| B-13 | Incidents per month (selected pipelines) | Qualifying failures | Databricks run history | `<<FILL>>` |
| B-14 | Distribution by incident type | Count per IC-nn | Run history + tickets | `<<FILL>>` |
| B-15 | Recurrence rate | % that are a repeat of a prior incident | Tickets / interviews | `<<FILL>>` |
| B-16 | Unresolved / no-root-cause rate | % closed without an identified cause | Tickets | `<<FILL>>` |
| B-17 | False-positive alert rate | % of alerts needing no action | Alerting system | `<<FILL>>` |

B-15 and B-16 are the strongest arguments for the knowledge-retrieval capability, and B-16 is also the honest counterweight: incidents closed without a cause today may not be diagnosable by NEXUS either.

### 2.4 Business impact

| ID | Metric | Definition | Source | Value |
|---|---|---|---|---|
| B-18 | Data-availability delay per incident | Hours of stale or missing downstream data | Lineage + incident record | `<<FILL>>` |
| B-19 | Downstream consumers affected | Teams, dashboards, or products impacted | Lineage | `<<FILL>>` |
| B-20 | SLA breaches attributable to these incidents | Count in window | SLA reporting | `<<FILL>>` |
| B-21 | Business cost of delay | Stated or estimated | Business owner | `<<FILL>>` |
| B-22 | Loaded hourly engineer cost | For the value model | Finance | `<<FILL>>` |

### 2.5 Evidence and governance baseline

| ID | Metric | Definition | Source | Value |
|---|---|---|---|---|
| B-23 | Systems opened per investigation | Tool sprawl | Interviews (05) | `<<FILL>>` |
| B-24 | Incidents with a reconstructable evidence trail | % where an auditor could later verify what was checked | Tickets | `<<FILL>>` |
| B-25 | Runbook coverage | % of incident types with current documented guidance | Doc review | `<<FILL>>` |
| B-26 | Runbook usage rate | % of incidents where a runbook was actually opened | Interviews | `<<FILL>>` |

B-24 is worth measuring even though nobody asks for it today. "Complete audit trail of every investigation" is one of NEXUS's clearest wins, and it is invisible unless the current state is recorded.

## 3. Value model inputs

From the proposal:

```
Direct monthly productivity value
    = incidents/month  x  minutes saved/incident  x  loaded hourly cost  /  60
```

| Input | Source | Value |
|---|---|---|
| Incidents per month | B-13 | `<<FILL>>` |
| Minutes saved per incident (hypothesis) | B-01/B-07 x target reduction | `<<FILL>>` |
| Loaded hourly cost | B-22 | `<<FILL>>` |
| **Direct monthly value (hypothesis)** | computed | `<<FILL>>` |

Record separately, and do not fold into the number above: risk avoidance, faster recovery, reduced repeat incidents, and improved auditability. The proposal notes these may dominate the direct labour value; conflating them makes the direct figure unfalsifiable.

## 4. Sampling protocol where telemetry is absent

Expect ticket data to be incomplete. Use this in preference to guessing:

1. Draw a **random** sample of 15-20 failed runs from the last 90 days on the selected pipelines. Random, not memorable - memorable incidents are systematically the worst ones and will inflate the baseline.
2. For each, reconstruct the timeline from run history, ticket, and channel history.
3. Where timestamps are missing, ask the engineer who handled it for a bounded estimate (best case / typical / worst case).
4. Report median and interquartile range, not a single mean.
5. Record sample size, method, and known bias next to every derived figure.
6. Have the pilot engineering champion sanity-check the result: "does this match your experience?"

**Bias to declare explicitly:** an inflated baseline makes the pilot look better and is the easiest way to produce a Gate 6 result nobody believes. If the sampled baseline is materially lower than the team's intuition, publish the sampled number and note the discrepancy.

## 5. Post-pilot comparison design

Agreed at Gate 0 so it cannot be rationalised later.

| Question | Decision |
|---|---|
| Comparison method | `<<FILL: before/after on same pipelines | Product lead | Fri 11 Sep>>` |
| Is a control group feasible? | `<<FILL: non-NEXUS engineers on the same incidents>>` |
| Minimum incidents for a credible result | `<<FILL: recommend >= 20 in the pilot window>>` |
| Who adjudicates "useful diagnosis"? | `<<FILL: recommend pilot champion, not the build team>>` |
| Confounders to record | Seasonality, team changes, pipeline changes, incident-mix shift |

**Adjudication independence matters.** If the team that built the agent also decides which diagnoses were useful, Gate 6 has no evidential value.

## 6. Sign-off

| Role | Name | Confirms | Date |
|---|---|---|---|
| Operations lead | | Baselines collected, methods documented | |
| Data engineering lead | | Figures match team experience | |
| Product lead | | Sufficient for Gate 6 comparison | |
| Executive sponsor | | Accepted as the measurement basis | |
