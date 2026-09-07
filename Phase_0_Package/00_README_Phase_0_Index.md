# NEXUS Phase 0 Package - Business Definition and Pilot Selection

> **Phase:** 0 of 6 (MVP programme)
> **Window:** Monday 7 September - Friday 11 September 2026 (Week 1)
> **Gate 0 review:** Friday 11 September 2026
> **Phase 1 start (conditional on Gate 0):** Monday 14 September 2026
> **Owner:** Product lead
> **Package version:** 1.0 (issued 7 September 2026)

---

## 1. What this package is

Phase 0 exists to prevent the programme's most likely failure mode: *building a technically impressive agent without a measurable business outcome*. This package contains every artifact the delivery plan requires before implementation may start.

It is issued in two states:

| State | Meaning | How to spot it |
|---|---|---|
| **Derived** | Already complete. Content follows deterministically from the approved proposal, PRD, delivery plan, or Solution Design Document. Review and ratify; do not rewrite. | No fill markers present |
| **Discovery** | Requires facts only the pilot team and system owners hold. Issued as a structured instrument with the exact question, the collection method, and the owner. | Contains `<<FILL: ...>>` markers |

**No placeholder has been invented as if it were a finding.** Pipeline names, engineer names, incident volumes, and baseline timings are left explicitly open rather than fabricated, because Gate 0 approves a real investment against them.

Find every open item:

```bash
grep -rn "<<FILL:" /Users/shravan/GitHub/Project_Nexus/Phase_0_Package
```

---

## 2. Contents

| # | Document | State | Owner | Due |
|---|---|---|---|---|
| 01 | [Pilot Charter](01_Pilot_Charter.md) | Discovery | Product lead + Sponsor | Thu 10 Sep |
| 02 | [Pilot Pipeline Inventory](02_Pilot_Pipeline_Inventory.md) | Discovery | Data engineering lead | Wed 9 Sep |
| 03 | [Supported Incident Types](03_Supported_Incident_Types.md) | Derived + selection | Data engineering lead | Wed 9 Sep |
| 04 | [Stakeholder and Responsibility Matrix](04_Stakeholder_and_Responsibility_Matrix.md) | Discovery | Product lead | Tue 8 Sep |
| 05 | [Current-State Incident Workflow](05_Current_State_Incident_Workflow.md) | Discovery | Product lead + UX | Wed 9 Sep |
| 06 | [Baseline Metrics Workbook](06_Baseline_Metrics_Workbook.md) | Discovery | Operations lead | Thu 10 Sep |
| 07 | [Access Requirements and Security Assessment](07_Access_Requirements_and_Security_Assessment.md) | Derived + approval | Security engineer | Thu 10 Sep |
| 08 | [Data Classification and Retention Constraints](08_Data_Classification_and_Retention_Constraints.md) | Derived + approval | Security and privacy | Thu 10 Sep |
| 09 | [Success Criteria and Pilot Scorecard](09_Success_Criteria_and_Pilot_Scorecard.md) | Derived + baselining | Product lead | Thu 10 Sep |
| 10 | [Product Backlog](10_Product_Backlog.md) | Derived | Product owner | Wed 9 Sep |
| 11 | [Evaluation Dataset Plan](11_Evaluation_Dataset_Plan.md) | Derived + scheduling | Applied AI lead | Tue 8 Sep |
| 12 | [RAID Log](12_RAID_Log.md) | Derived | Product lead | Continuous |
| 13 | [Gate 0 Decision Pack](13_Gate_0_Decision_Pack.md) | Assembled Fri | Sponsor | Fri 11 Sep |

Already approved upstream and referenced, not reproduced here: the Product Requirements Document, business proposal, and reference architecture (`NEXUS_Business_Proposal_PRD_Architecture_v0.1.pdf`), the delivery plan (`NEXUS_Project_Phases_and_Delivery_Plan_v1.0.md`), and the Solution Design Document (`NEXUS_Solution_Design_Document_v1.0.md`).

---

## 3. Week 1 schedule

| Day | Activity | Output |
|---|---|---|
| **Mon 7 Sep** | Kickoff. Confirm sponsor and pilot domain candidates. Issue this package. Start evaluation-set labelling recruitment (long pole - see 11). | Domain shortlist |
| **Tue 8 Sep** | Persona and stakeholder interviews. Responsibility matrix. Evaluation labelling protocol agreed. | 04, 11 |
| **Wed 9 Sep** | Pipeline inventory walkthrough with system owners. Incident-type selection. Current-state workflow mapping session. Backlog review. | 02, 03, 05, 10 |
| **Thu 10 Sep** | Baseline metric extraction. Access request submission. Data-classification review. Charter and success criteria drafted. | 01, 06, 07, 08, 09 |
| **Fri 11 Sep** | **Gate 0 review.** Approve or defer. | 13 |

**Critical path:** access approvals (07) and evaluation-set labelling (11) have the longest lead times and are the two items most likely to delay Phase 2 and Phase 3 respectively. Both start Monday, not when their phase begins.

---

## 4. Gate 0 exit criteria (from the delivery plan)

Gate 0 passes only when every line is true:

- [ ] One pilot team is confirmed, with a named engineering champion
- [ ] Three to five representative pipelines are selected and their owners identified
- [ ] Required evidence sources are identified and confirmed available
- [ ] Data and system owners are known and have acknowledged the access request
- [ ] Product scope is approved, with exclusions explicit
- [ ] Access owners are assigned and the approval path is agreed
- [ ] Baseline metrics are documented (or a documented sampling protocol is agreed where telemetry is absent)
- [ ] Success measures are accepted by business **and** engineering stakeholders
- [ ] No unresolved issue prevents development from starting

Two additions this package makes to that list, arising from the Solution Design Document:

- [ ] Open decisions D-01, D-05, D-06 and finding A-1 are closed (see 13)
- [ ] The evaluation-set labelling schedule is committed by named labellers

---

## 5. Standing conventions

- **Fill marker:** `<<FILL: description | owner | due>>`
- **Traceability:** items referencing PRD user stories use `US-nn`; open proposal decisions use `D-nn`; SDD analysis findings use `A-nn`; backlog items use `NX-nnn`; RAID entries use `R/A/I/D-nn`.
- **No invented facts.** If a number cannot be sourced, it stays a fill marker and the gap is raised at Gate 0.
