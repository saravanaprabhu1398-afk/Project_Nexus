# 12 - Project RAID Log

> **Status:** Live document, reviewed weekly | **Owner:** Product lead | **Opened:** Monday 7 September 2026
> **R**isks · **A**ssumptions · **I**ssues · **D**ependencies

---

## Scoring

**Probability / Impact:** 1 low · 2 medium · 3 high · **Score** = P x I (1-9)
**Status:** Open · Mitigating · Closed · Accepted · Escalated

---

## 1. Risks

| ID | Risk | P | I | Score | Owner | Response | Trigger to escalate | Status |
|---|---|---|---|---|---|---|---|---|
| R-01 | Incomplete or low-quality telemetry on the selected pipelines yields weak diagnoses | 2 | 3 | 6 | Data eng lead | Evidence criteria C2-C5 gate pipeline selection (doc 02); expose missing evidence explicitly rather than guessing | Any selected pipeline fails an evidence criterion | Open |
| R-02 | Hallucinated or unsupported conclusions destroy engineer trust | 2 | 3 | 6 | Applied AI lead | Citation binding, Evaluator guardrail (NX-087), banded confidence, abstention path, golden-set scoring | Any unsupported claim reaches a pilot user | Open |
| R-03 | Evaluation labelling under-resourced; Gate 3 has no evidence | **3** | **3** | **9** | Applied AI lead | Start Week 1; named labellers with committed hours as a Gate 0 exit condition (doc 11) | Labellers not named by Tue 8 Sep | **Open - highest score** |
| R-04 | Access approvals delayed; Phase 2 starts without Databricks access | **3** | **3** | **9** | Security engineer | Submit all requests Week 1 including the Week 9 production grant; track in doc 07 §3 | Any Phase 2 grant unapproved by Fri 18 Sep | **Open - highest score** |
| R-05 | Unauthorized data exposure through logs reaching the model provider | 2 | 3 | 6 | Security engineer | Two-stage redaction at the gateway before persistence and prompt (NX-066); redaction false-negative testing | Any secret or PII found in a prompt or trace | Open |
| R-06 | Model or infrastructure cost undermines the business case | 2 | 3 | 6 | Architect | Budgets from Phase 1 (NX-012); cost-per-diagnosis metric from Phase 1 (NX-035); model routing; caching; context minimization | Cost per investigation exceeds the Gate 0 ceiling | Open |
| R-07 | Scope expansion toward write actions during the pilot | 2 | 3 | 6 | Sponsor | Read-only boundary in the charter; write enablement requires a new gate with a new threat model | Any request to enable a write path | Open |
| R-08 | Excessive pilot scope delays delivery and blurs the value signal | 2 | 2 | 4 | Product owner | 3-5 pipelines, 4-6 incident categories, explicit exclusions | Selection exceeds the stated bounds | Open |
| R-09 | Low engineer adoption in Weeks 10-11 | 2 | 3 | 6 | Product owner | Workflow-centred UX from doc 05 findings; pilot champions; shadow mode generating value before users are asked to change behaviour | Fewer than half of pilot users complete an investigation in Week 10 | Open |
| R-10 | Insufficient incident volume during the pilot window for a credible result | 2 | 3 | 6 | Product lead | Volume criterion C1 in selection; shadow mode from Phase 5 to accumulate cases; historical replay as a supplement | Fewer than 10 qualifying incidents by mid Week 11 | Open |
| R-11 | Prompt injection via log content or runbooks | 2 | 3 | 6 | Security engineer | Quarantine from Phase 3 (NX-095); capability floor - writes structurally absent; output scanning; adversarial subset | Any injection case succeeds in testing | Open |
| R-12 | Platform lock-in makes the portability claim untrue | 2 | 2 | 4 | Architect | Evidence envelope enforced by lint and contract test (NX-058); ModelAdapter; standard tool contract | Any provider type found above the gateway | Open |
| R-13 | Security review capacity unavailable in Weeks 8-9 | 2 | 3 | 6 | Security engineer | Book the review slot in Week 1; incremental security involvement from Phase 1 so Phase 4 is confirmation, not discovery | Review slot not booked by Fri 11 Sep | Open |
| R-14 | Model provider terms do not permit the required data handling | 2 | 3 | 6 | Architect | Confirm by Gate 1 (D-06); fallback to an in-tenant endpoint with a revised cost model | Terms unconfirmed by Gate 1 | Open |
| R-15 | Baseline is inflated or unrepresentative, invalidating the Gate 6 comparison | 2 | 3 | 6 | Operations lead | Random sampling protocol (doc 06 §4); champion sanity check; independent adjudication of usefulness | Sampled baseline diverges materially from team intuition | Open |
| R-16 | The steps NEXUS automates are a minority of elapsed triage time, making SC-03 unreachable | 2 | 3 | 6 | Product lead | Test explicitly in doc 05 §6; renegotiate SC-03 at Gate 0 rather than miss it at Gate 6 | Evidence collection < 40% of elapsed time | Open |
| R-17 | Deterministic components (resolver, diffing) prove harder than expected, pushing work to the model | 1 | 2 | 2 | Applied AI lead | Build the deterministic path first in Phase 2 so the gap is known before Phase 3 | Resolver ambiguity rate above 20% | Open |
| R-18 | Key person dependency on the pilot champion | 2 | 2 | 4 | Product lead | Name two champions, not one | Single champion becomes unavailable | Open |

## 2. Assumptions

| ID | Assumption | Owner | Validate by | Impact if false | Status |
|---|---|---|---|---|---|
| A-01 | Databricks API access, log retention, and catalog metadata are available for the selected pipelines within Week 2 | Data eng lead | Wed 9 Sep | Phase 2 blocked; pipeline reselection required | Open |
| A-02 | At least 30 labellable historical incidents exist with surviving evidence | Data eng lead | Wed 9 Sep | Evaluation set undersized; Gate 3 confidence weakened | Open |
| A-03 | Pilot engineers are available for interviews, labelling, and pilot usage | Pilot owner | Tue 8 Sep | R-03 and R-09 materialize | Open |
| A-04 | Model provider terms permit no-training use of prompt data | Architect | Gate 1 | R-14 materializes; cost model changes | Open |
| A-05 | Security review capacity exists in Weeks 8-9 | Security | Fri 11 Sep | Gate 4 slips; pilot delayed | Open |
| A-06 | Log retention on the selected pipelines exceeds 14 days | Data eng lead | Wed 9 Sep | Evidence unavailable for recent incidents | Open |
| A-07 | User delegation to Databricks and Unity Catalog is technically supported | Architect | Gate 1 | Falls back to a service identity; broader access review needed | Open |
| A-08 | Incident volume on the selected pipelines is >= 10/month | Data eng lead | Wed 9 Sep | R-10 materializes | Open |
| A-09 | Runbooks exist and are current enough to be worth retrieving | Data eng lead | Wed 9 Sep | Knowledge retrieval delivers little; Phase 3 scope reduces | Open |
| A-10 | The 7-phase delivery plan governs, not the PDF's 5-stage summary | Product lead | Gate 0 | Reporting confusion; inconsistent gate expectations | Open |

## 3. Issues

Issues are things that are already true, not risks. The first ten are the findings carried from the Solution Design Document's analysis of the source documents.

| ID | Issue | Raised | Severity | Owner | Resolution required by | Status |
|---|---|---|---|---|---|---|
| I-01 | **A-1** Timeline mismatch: PDF's five stages vs the plan's seven phases | 7 Sep | Medium | Product lead | Gate 0 | Open |
| I-02 | **A-2** Policy engine is a Phase 4 deliverable, but "100% policy-checked" applies from the first Phase 2 tool call | 7 Sep | High | Architect | Gate 1 - **design resolved**: PDP interface built in Phase 1 (NX-038) | Mitigating |
| I-03 | **A-3** Phase 3 requires code-change correlation; no repository connector exists until Phase 7 | 7 Sep | Medium | Product owner | **Gate 1 decision:** add a narrow read-only metadata tool (NX-062) or descope (doc 03 confirms no category depends on it) | Open |
| I-04 | **A-4** US-07 is a P1 MVP story but event triggering is Phase 8 | 7 Sep | Medium | Product owner | Gate 4 - **design resolved**: shadow-mode webhook in Phase 5 (NX-130) | Mitigating |
| I-05 | **A-5** Vector store appears in the Phase 1 architecture but knowledge retrieval is Phase 3 | 7 Sep | Low | Architect | Gate 1 - **resolved**: provision P1, populate P3 (NX-026) | Closed |
| I-06 | **A-6** 2s acknowledgement and 5-minute diagnosis are incompatible with a synchronous API | 7 Sep | High | Architect | Gate 1 - **resolved**: async API (ADR-01, NX-002) | Closed |
| I-07 | **A-7** Numeric confidence in the product mock implies a calibration method no phase delivers | 7 Sep | Medium | Applied AI lead | Gate 3 - **resolved**: banded confidence (ADR-06, NX-082) | Mitigating |
| I-08 | **A-8** Phase 3 ingests logs and runbooks - the injection surface - before Phase 4's injection defence | 7 Sep | High | Security engineer | Gate 3 - **design resolved**: quarantine moved to Phase 3 (NX-095) | Mitigating |
| I-09 | **A-9** Phase 2 persists raw payloads while retention (D-07) is still open | 7 Sep | High | Data privacy | Gate 0 - doc 08 proposes defaults; purge job in Phase 2 (NX-061) | Mitigating |
| I-10 | **A-10** No multi-tenancy model despite tenant in the request contract and isolation tests in Phase 4 | 7 Sep | High | Architect | Gate 1 - **resolved**: tenant partitioning from Phase 1 (NX-021) | Mitigating |
| I-11 | Gate 3 quality thresholds (SC-07, SC-08, SC-10, SC-11) are not derivable from the source documents | 7 Sep | Medium | Sponsor | **Gate 0 ratification required** | Open |
| I-12 | SC-21 pilot usefulness threshold is undefined ("agreed before pilot") | 7 Sep | Medium | Sponsor | Gate 0 | Open |
| I-13 | SC-26 cost-per-diagnosis ceiling is undefined | 7 Sep | Medium | Sponsor | Gate 0 | Open |
| I-14 | Open decisions D-01 through D-08 remain unclosed | 7 Sep | High | Product lead | D-01, D-05, D-06 by Gate 0; remainder per doc 13 | Open |

## 4. Dependencies

| ID | Dependency | On whom | Needed by | Lead time | Status |
|---|---|---|---|---|---|
| D-01 | Databricks workspace read access (AC-01..05) | Workspace admin | Mon 28 Sep (Phase 2) | `<<FILL>>` | Requested |
| D-02 | Unity Catalog metadata access (AC-06..09) | UC governance owner | Mon 28 Sep | `<<FILL>>` | Requested |
| D-03 | Non-production workspace (AC-10) | Workspace admin | Mon 21 Sep (Phase 1 testing) | `<<FILL>>` | Requested |
| D-04 | Runbook and incident-record access (AC-11..13) | Doc / ITSM owners | Mon 12 Oct (Phase 3) | `<<FILL>>` | Requested |
| D-05 | Repository metadata access (AC-14) | Repo owner | Conditional on I-03 | `<<FILL>>` | Held |
| D-06 | Enterprise IdP registration (AC-15..16) | IAM team | Mon 26 Oct (Phase 4) | `<<FILL>>` | Requested |
| D-07 | **Production read access (AC-20)** | Workspace admin + system owners | Mon 9 Nov (Phase 5) | **Longest - request now** | Requested |
| D-08 | Security review slot | Security | Weeks 8-9 | Book Week 1 | `<<FILL>>` |
| D-09 | Pilot engineer time for labelling | Pilot owner | Weeks 2-4 | 20-30h | `<<FILL>>` |
| D-10 | Pilot engineer time for usage | Pilot owner | Weeks 10-11 | `<<FILL>>` | `<<FILL>>` |
| D-11 | Model provider contract / DPA | Procurement + Legal | Gate 1 | `<<FILL>>` | `<<FILL>>` |
| D-12 | Cloud subscription and budget approval | Platform + Finance | Mon 14 Sep (Phase 1) | `<<FILL>>` | `<<FILL>>` |
| D-13 | Teams/Slack and Jira app registration | Collaboration + Jira admins | Mon 9 Nov (Phase 5) | `<<FILL>>` | `<<FILL>>` |

## 5. Review

Reviewed weekly by the product lead with named owners. Scores are re-evaluated at every gate. Any risk reaching score 9, or any issue rated High and unresolved at its gate, is escalated to the sponsor.

**Currently at score 9:** R-03 (evaluation labelling) and R-04 (access approvals). Both are Week 1 actions with long tails, and both are on the critical path for gates 3 and 2 respectively. They are the two items the sponsor should ask about first at Gate 0.
