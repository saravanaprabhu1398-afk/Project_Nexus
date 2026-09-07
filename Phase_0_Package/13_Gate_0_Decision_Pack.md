# 13 - Gate 0 Decision Pack

> **Gate:** 0 - Approve MVP investment and pilot scope
> **Date:** Friday 11 September 2026 | **Chair:** Executive sponsor
> **Board:** Sponsor, product owner, technical architect, security and privacy, data engineering lead, pilot-team owner
> **Outcome options:** Approve · Approve with conditions · Defer pending named items · Do not proceed

---

## 1. Decision requested

Authorize a 12-week, read-only MVP pilot of NEXUS against a named pilot domain, funded per section 6, delivered through seven gated phases, with a production go/no-go decision at Gate 6 on 27 November 2026.

## 2. Agenda (90 minutes)

| Min | Item | Lead |
|---|---|---|
| 0-10 | Problem, baseline, and value hypothesis | Product lead |
| 10-20 | Pilot definition: domain, pipelines, incident types, users | Data eng lead |
| 20-30 | Scope boundary and what is explicitly excluded | Product owner |
| 30-40 | Solution design summary and the ten source-document findings | Technical architect |
| 40-50 | Access, security, and data-handling position | Security + privacy |
| 50-65 | **Decisions requested** (section 4) | Sponsor |
| 65-80 | Risks, dependencies, and the two critical-path items | Product lead |
| 80-90 | Decision and conditions | Sponsor |

## 3. Evidence pack

| # | Document | Status |
|---|---|---|
| 01 | Pilot Charter | `<<FILL>>` |
| 02 | Pilot Pipeline Inventory | `<<FILL>>` |
| 03 | Supported Incident Types | `<<FILL>>` |
| 04 | Stakeholder and Responsibility Matrix | `<<FILL>>` |
| 05 | Current-State Incident Workflow | `<<FILL>>` |
| 06 | Baseline Metrics Workbook | `<<FILL>>` |
| 07 | Access Requirements and Security Assessment | `<<FILL>>` |
| 08 | Data Classification and Retention Constraints | `<<FILL>>` |
| 09 | Success Criteria and Pilot Scorecard | `<<FILL>>` |
| 10 | Product Backlog | `<<FILL>>` |
| 11 | Evaluation Dataset Plan | `<<FILL>>` |
| 12 | RAID Log | `<<FILL>>` |
| - | PRD, business proposal, reference architecture (v0.1) | Approved upstream |
| - | Solution Design Document v1.0 | Issued 7 Sep |

## 4. Decisions requested at this gate

### 4.1 Must close at Gate 0

| ID | Decision | Recommendation | Decided |
|---|---|---|---|
| **D-01** | Pilot domain and team | `<<FILL: from doc 01>>` | |
| **D-05** | Evaluation truth set - who labels, when | Pilot engineers label; **20-30 hours committed in Weeks 2-4**; named individuals, not a team pledge | |
| **D-06** | Model posture | Two approved classes behind the ModelAdapter; no-training terms contractually confirmed by Gate 1; in-tenant endpoint as the documented fallback | |
| **A-1 / I-01** | Which timeline governs | **The 7-phase delivery plan governs.** The PDF's 5-stage view is a summary and is retired from programme reporting | |
| **I-11** | Gate 3 quality thresholds | Adopt the SDD proposals as provisional (top-1 >= 60%, top-3 >= 80%, calibration >= 85%, abstention >= 70%), reviewed once the golden set exists and its difficulty is known | |
| **I-12** | SC-21 pilot usefulness threshold | `<<FILL: sponsor to set>>` | |
| **I-13** | SC-26 cost-per-diagnosis ceiling | `<<FILL: sponsor to set>>` | |
| **SC-03** | Triage-reduction target, after the doc 05 §6 analysis | Confirm 50%, or restate as a reduction in the addressable segment if evidence collection is a minority of elapsed time | |

### 4.2 Direction now, closure later

| ID | Decision | Recommendation | Close by |
|---|---|---|---|
| **D-02** | Hosting and residency | Co-locate runtime, state, and model endpoint in the pilot's data region; telemetry exports metadata, never span content | Gate 1 |
| **D-03** | Identity model | **User delegation primary**, narrow service identity only for shared knowledge sources | Gate 1 |
| **D-04** | Knowledge scope | Pilot-team runbooks and resolved incidents for the selected pipelines only, with per-source owner sign-off | Gate 2 |
| **D-07** | Retention | Raw payloads 30d, operational facts 90d, trace and audit 1y, per doc 08; purge job ships in Phase 2 | Gate 2 |
| **D-08** | Scale gate | The doc 09 scorecard plus zero unresolved critical security findings | Gate 6 |
| **A-3 / I-03** | Code correlation in MVP | Doc 03 confirms no supported incident category depends on it. Include only if repository metadata access is grantable without delaying Phase 2; otherwise descope and emit as missing evidence | Gate 1 |

## 5. Design positions taken (for information, not decision)

Resolved in the Solution Design Document; noted here so the board sees where the source documents were inconsistent and how the design closed the gap.

| Finding | Position |
|---|---|
| A-2 Policy timing | PDP interface and audit sink built in Phase 1 with a deny-by-default allowlist, so "100% policy-checked" holds from the first Databricks call |
| A-6 Latency | Investigation API is asynchronous; 202 plus polling or event stream |
| A-7 Confidence | Banded (High/Medium/Low/Abstain) with published criteria, not a decimal |
| A-8 Injection | Untrusted-content quarantine moves from Phase 4 to Phase 3, ahead of runbook and log ingestion |
| A-9 Retention | Retention defaults and a tested purge job ship with the first persistence in Phase 2 |
| A-10 Tenancy | Tenant partitioning from Phase 1; no un-tenanted query method exists |
| A-4 Event trigger | Shadow-mode webhook in Phase 5 satisfies US-07 without importing Phase 8 |
| A-5 Vector store | Provisioned Phase 1, populated Phase 3 |

## 6. Investment

| Item | Amount | Basis |
|---|---|---|
| Team, 12 weeks | `<<FILL>>` | Charter §7 |
| Model inference | `<<FILL>>` | Budgets in SDD 9.6 |
| Infrastructure | `<<FILL>>` | SDD 14 |
| Contingency 15% | `<<FILL>>` | |
| **Total** | `<<FILL>>` | |

Against a direct monthly productivity value hypothesis of `<<FILL>>` (doc 06 §3), plus separately tracked risk-avoidance, recovery, recurrence, and auditability benefits.

## 7. What the board is buying

An **evidence-based decision at Gate 6**, not a guaranteed product. The pilot is explicitly designed so that a "stop" outcome is a successful use of the investment: it costs 12 weeks to learn whether governed AI investigation works on this platform, against the alternative of learning it after a production rollout.

The design also front-loads the reusable parts. The identity, policy, audit, evidence, and evaluation foundations built in Phases 1-4 are the prerequisites for any future agentic engineering capability, whether or not this particular investigator scales.

## 8. Exit criteria checklist

| # | Criterion | Met |
|---|---|---|
| 1 | One pilot team confirmed, with a named champion | ☐ |
| 2 | Three to five representative pipelines selected | ☐ |
| 3 | Evidence sources identified and confirmed available | ☐ |
| 4 | Data and system owners known and engaged | ☐ |
| 5 | Product scope approved with explicit exclusions | ☐ |
| 6 | Access owners assigned; requests submitted | ☐ |
| 7 | Baseline metrics documented, or a sampling protocol agreed | ☐ |
| 8 | Success measures accepted by business and engineering | ☐ |
| 9 | No unresolved issue prevents development from starting | ☐ |
| 10 | D-01, D-05, D-06 and finding A-1 closed | ☐ |
| 11 | **Evaluation labellers named with committed hours** (R-03) | ☐ |
| 12 | **All Phase 2 and Phase 5 access requests submitted** (R-04) | ☐ |
| 13 | Security review slot booked for Weeks 8-9 (R-13) | ☐ |

Items 11-13 are additions this package makes to the delivery plan's list. Each corresponds to a long-lead item that, if left until its own phase, causes a gate to slip.

## 9. If the gate does not pass

| Situation | Recommended action |
|---|---|
| Pilot domain not agreed | Defer one week; the rest of the package is domain-independent and stands |
| Insufficient incident volume or evidence on candidate pipelines | Widen the candidate set before narrowing; do not proceed on pipelines that fail the evidence criteria |
| Fewer than 30 labellable historical incidents | Extend labelling into Phases 1-2, or accept a smaller set with explicitly reduced Gate 3 confidence - stated, not discovered |
| Access approvals not achievable in the window | Defer the programme rather than start Phase 1 hoping access arrives; Phase 1 has value only if Phase 2 can follow |
| Security or privacy position unresolved | Defer; a read-only pilot on production data cannot start on an unresolved data-handling question |

## 10. Decision record

| Role | Name | Decision | Date | Conditions / notes |
|---|---|---|---|---|
| Executive sponsor | | | | |
| Product owner | | | | |
| Technical architect | | | | |
| Security and privacy | | | | |
| Data engineering lead | | | | |
| Pilot-team owner | | | | |

**Outcome:** ☐ Approve ☐ Approve with conditions ☐ Defer ☐ Do not proceed

**Conditions:** `<<FILL>>`

**Phase 1 authorized to start:** ☐ Monday 14 September 2026 ☐ Other: `<<FILL>>`
