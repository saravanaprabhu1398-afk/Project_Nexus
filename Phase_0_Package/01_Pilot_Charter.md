# 01 - NEXUS Pilot Charter

> **Status:** Draft for Gate 0 approval | **Owner:** Product lead | **Due:** Thursday 10 September 2026

---

## 1. Purpose

Authorize a 12-week, read-only MVP pilot of NEXUS with a single named engineering domain, to establish whether an evidence-backed AI investigator materially reduces incident triage time without weakening access control or introducing production risk.

## 2. Problem statement

Data-platform incident diagnosis today passes through approximately six handoffs before a credible answer exists: alert fires, owner is located, evidence is collected from logs and configs and lineage and code, change is reconstructed, a hypothesis is formed from experience, and an action is recommended. Each handoff adds delay, loses context, and increases dependence on the specific engineer who already knows the system.

The cost is not only engineering hours. It is longer incident duration, interruption of senior specialists, resolution knowledge that stays tribal, and an evidence chain too weak to reconstruct after the fact.

## 3. Pilot objective

At the end of the pilot, a pilot engineer should be able to ask *"Why did the customer ingestion pipeline fail?"* and receive, within five minutes, a diagnosis that names a likely root cause, links every material claim to an inspectable artifact, separates fact from hypothesis, states what evidence is missing, and recommends the next engineering action - with a complete audit trail of every tool call and data access.

## 4. Pilot definition

| Field | Value |
|---|---|
| Pilot domain / business area | `<<FILL: which business domain | Sponsor | Wed 9 Sep>>` |
| Pilot engineering team | `<<FILL: team name | Sponsor | Wed 9 Sep>>` |
| Team size / pilot user count | `<<FILL: number of engineers who will use NEXUS | Eng lead | Wed 9 Sep>>` |
| Named engineering champion | `<<FILL: name | Eng lead | Wed 9 Sep>>` |
| Databricks workspace(s) in scope | `<<FILL: workspace ids | Data platform | Wed 9 Sep>>` |
| Pipelines in scope | 3-5, listed in [02](02_Pilot_Pipeline_Inventory.md) |
| Incident types in scope | Listed in [03](03_Supported_Incident_Types.md) |
| Duration | 12 weeks, 7 Sep - 27 Nov 2026 |
| Pilot usage window (Phase 5) | Weeks 10-11 |

**Domain selection criteria** (apply to candidate domains before choosing):

1. Sufficient incident volume to produce a measurable result within a two-week pilot window - roughly 10+ qualifying failures per month.
2. Adequate evidence: run history, retained logs, and catalog metadata actually available for the selected pipelines.
3. Willing users. A team that does not want the tool will not generate usable feedback.
4. A business owner who can articulate the cost of delayed data availability.
5. Data sensitivity that security can approve for a pilot within Week 1-2, not a quarter.

## 5. Scope

### In scope (MVP)

- Manual prompt and Databricks job-failure trigger
- Job, task, cluster, log, and run-history inspection
- Schema and lineage context where authorized
- Runbook and past-incident retrieval
- Root-cause hypotheses with confidence banding and cited evidence
- Recommended next action and escalation path
- Full trace, access log, and outcome feedback

### Explicitly out of scope

- Autonomous code changes or pull requests
- Production deployment, rollback, or job restart
- Cross-domain unrestricted access
- Automated incident closure
- Multi-agent debate or self-directed long-running tasks
- Predictive anomaly detection as a core feature
- Replacement of existing monitoring or ITSM platforms

**Operating boundary:** the MVP is read-only by construction. No write-capable credential is issued to the runtime. Exclusions are not deferrals of intent within this pilot; adding any of them requires a new governance gate.

## 6. What the pilot must prove

| Proof | Evidence at Gate 6 |
|---|---|
| Speed | Time to first useful diagnosis versus baseline |
| Quality | Diagnosis accuracy and evidence coverage against a labelled set |
| Trust | Engineer usefulness rating; correction rate; abstention behaviour |
| Control | 100% of tool calls policy-checked and audited; zero unauthorized writes |
| Economics | Cost per useful diagnosis against realized time saved |

Targets are in [09](09_Success_Criteria_and_Pilot_Scorecard.md). They are hypotheses to validate, not guaranteed outcomes.

## 7. Team and commitment

| Role | Name | Commitment | Source |
|---|---|---|---|
| Executive sponsor | `<<FILL | - | Mon 7 Sep>>` | Decision authority | - |
| Product owner | `<<FILL>>` | Full time | Appendix A |
| Technical architect | `<<FILL>>` | Full time | Appendix A |
| Backend/platform engineer x2 | `<<FILL>>` | Full time | Appendix A |
| Data/Databricks engineer | `<<FILL>>` | Full time | Appendix A |
| Applied AI engineer | `<<FILL>>` | Full time | Appendix A |
| Security engineer | `<<FILL>>` | Fractional | Appendix A |
| Product/UX designer | `<<FILL>>` | Fractional | Appendix A |
| SRE/operations representative | `<<FILL>>` | Fractional | Appendix A |
| Pilot engineering champions | `<<FILL>>` | ~2h/week each | Appendix A |

Additional Phase 0 commitment: pilot engineers must allocate time to label the evaluation set (see [11](11_Evaluation_Dataset_Plan.md)). This is the single most commonly under-resourced item in the programme.

## 8. Budget envelope

| Item | Estimate | Basis |
|---|---|---|
| Team cost, 12 weeks | `<<FILL: loaded cost | Finance | Thu 10 Sep>>` | Section 7 |
| Model inference (dev + pilot) | `<<FILL: estimate | Applied AI lead | Thu 10 Sep>>` | Budget caps in SDD 9.6 |
| Infrastructure (compute, Postgres, Redis, vector, telemetry) | `<<FILL>>` | SDD 14 |
| Contingency | 15% | Standard |

Cost telemetry is instrumented from Phase 1 so the Gate 6 economics case rests on measurement, not estimate.

## 9. Governance

| Decision | Authority |
|---|---|
| Investment and scope | Executive sponsor |
| Product priority within approved scope | Product owner |
| Architecture and technical standards | Technical architect |
| Access grants and security acceptance | Security and privacy + system owners |
| Pilot go/no-go per phase | Gate review board (sponsor, product, architecture, security, pilot owner) |
| Any expansion of the read-only boundary | Executive sponsor **and** security, at a formal gate |

Gates 0-6 are as defined in the delivery plan. A gate that cannot show its required evidence does not pass on schedule pressure.

## 10. Assumptions

1. Databricks API access, log retention, and catalog metadata for the selected pipelines are available within Week 2.
2. Representative historical incidents exist and are retrievable for evaluation labelling.
3. Pilot engineers are available for interviews (Week 1), labelling (Weeks 1-4), and pilot usage (Weeks 10-11).
4. Model provider terms permitting no-training use of prompt data are in place or obtainable by Gate 1.
5. Security review capacity is available in Weeks 8-9 without queueing.

Violated assumptions become issues in [12](12_RAID_Log.md).

## 11. Termination and pause conditions

The pilot pauses or stops if:

- Access or evidence controls prove unreliable (per the proposal's pilot decision rule)
- A critical security finding cannot be resolved or formally accepted
- Evidence quality is insufficient to support diagnosis on the selected pipelines by Gate 2
- Cost per investigation invalidates the business case before Gate 5
- Any unauthorized production write occurs - immediate stop and review

## 12. Approval

| Role | Name | Decision | Date | Notes |
|---|---|---|---|---|
| Executive sponsor | | | | |
| Product owner | | | | |
| Data engineering lead | | | | |
| Platform architecture | | | | |
| Security and privacy | | | | |
| Pilot-team owner | | | | |
