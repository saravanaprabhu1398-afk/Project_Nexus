# 04 - Stakeholder and Responsibility Matrix

> **Status:** Discovery instrument | **Owner:** Product lead | **Due:** Tuesday 8 September 2026

---

## 1. Stakeholder register

| ID | Role | Name | Org / team | Interest in NEXUS | Influence | Engagement mode |
|---|---|---|---|---|---|---|
| S-01 | Executive sponsor | `<<FILL>>` | | Funds the programme; owns the go/no-go | High | Gate reviews |
| S-02 | Product owner | `<<FILL>>` | | Owns scope, value, prioritization | High | Daily |
| S-03 | Technical architect | `<<FILL>>` | | Owns architecture and standards | High | Daily |
| S-04 | Platform engineering lead | `<<FILL>>` | | Owns the agent service | High | Daily |
| S-05 | Applied AI lead | `<<FILL>>` | | Owns reasoning, retrieval, evaluation | High | Daily |
| S-06 | Integration lead | `<<FILL>>` | | Owns connectors and evidence layer | High | Daily |
| S-07 | Security and architecture lead | `<<FILL>>` | | Owns identity, policy, threat model | High | Weekly + Gates 2/4 |
| S-08 | Data privacy / compliance | `<<FILL>>` | | Owns classification, retention, residency | Medium-High | Gates 0/4 |
| S-09 | Data engineering lead (pilot team) | `<<FILL>>` | | Owns pilot pipelines and domain expertise | High | Weekly |
| S-10 | Pilot engineering champions | `<<FILL>>` | | Validate scenarios, label data, use the product | High | Weekly |
| S-11 | Databricks platform / workspace admin | `<<FILL>>` | | Grants and controls workspace access | Medium | Weeks 1-2, then as needed |
| S-12 | Unity Catalog / data governance owner | `<<FILL>>` | | Grants catalog metadata access | Medium | Weeks 1-2 |
| S-13 | System owners (per pipeline) | `<<FILL>>` | | Approve read access to their systems | Medium | Week 1 |
| S-14 | SRE / operations representative | `<<FILL>>` | | Owns reliability, support model | Medium | Phases 5-6 |
| S-15 | Product / UX designer | `<<FILL>>` | | Owns investigation experience | Medium | Phases 0, 5 |
| S-16 | Identity / IAM team | `<<FILL>>` | | Enterprise IdP integration | Medium | Phase 4 |
| S-17 | Finance / business owner of pilot domain | `<<FILL>>` | | Owns the value case | Medium | Gates 0, 6 |
| S-18 | Internal audit | `<<FILL>>` | | Consumes the audit trail | Low-Medium | Phase 4, Gate 6 |

`<<FILL: complete register with names | Product lead | Tue 8 Sep>>`

## 2. RACI by programme activity

**R** Responsible · **A** Accountable (one only) · **C** Consulted · **I** Informed

| Activity | Sponsor | Prod owner | Architect | Platform | Applied AI | Integration | Security | Privacy | Data eng lead | Pilot champs | SRE | UX |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Pilot domain and scope selection | **A** | R | C | I | I | I | C | C | R | C | I | C |
| Pipeline inventory and selection | I | C | I | I | I | C | C | C | **A/R** | R | I | I |
| Incident-type selection | I | C | I | I | C | C | I | I | **A/R** | R | I | I |
| Baseline metric collection | I | **A** | I | I | I | I | I | I | R | R | R | C |
| Access request and approval | I | C | C | I | I | R | **A** | C | R | I | I | I |
| Data classification and retention | I | C | C | I | I | C | R | **A** | C | I | I | I |
| Success criteria definition | **A** | R | C | I | C | I | C | I | C | C | I | C |
| Product backlog and prioritization | I | **A/R** | C | C | C | C | C | I | C | C | I | C |
| Evaluation dataset labelling | I | C | I | I | **A** | I | I | C | R | **R** | I | I |
| Architecture decisions (ADRs) | I | C | **A/R** | R | R | R | C | I | C | I | C | I |
| Agent runtime and API build | I | C | C | **A/R** | C | C | I | I | I | I | I | I |
| Connector and evidence layer build | I | C | C | C | C | **A/R** | C | I | C | I | I | I |
| Reasoning, retrieval, prompts | I | C | C | I | **A/R** | C | I | I | C | C | I | I |
| Policy engine and authorization | I | I | C | R | I | R | **A/R** | C | I | I | I | I |
| Threat model and security testing | I | I | C | C | C | C | **A/R** | C | I | I | C | I |
| Pilot UI and experience | I | **A** | I | R | I | I | I | I | I | C | I | R |
| Pilot onboarding and support | I | **A** | I | C | I | I | I | I | C | R | R | C |
| Production-readiness assessment | C | C | R | R | C | C | R | C | C | I | **A** | I |
| Cost model and ROI | **A** | R | C | C | R | I | I | I | C | I | C | I |
| Gate decisions 0-6 | **A** | R | R | C | C | C | R | C | R | C | C | I |

## 3. Decision rights

| Decision class | Decided by | Consulted | Escalation |
|---|---|---|---|
| Scope change within an approved phase | Product owner | Architect, pilot champions | Sponsor |
| Scope change crossing a gate boundary | Sponsor | Full gate board | - |
| Architecture decision (ADR) | Technical architect | Engineering leads, Security | Sponsor if cost/schedule material |
| Any change to the read-only boundary | Sponsor **and** Security jointly | Full gate board | No unilateral path exists |
| Access grant to a new system or resource | System owner + Security | Architect, Integration lead | Sponsor |
| Data classification or retention change | Privacy/compliance | Security, Architect | Legal |
| Model provider or posture change | Architect | Applied AI, Security, Privacy | Sponsor |
| Evaluation threshold setting | Sponsor at Gate 0 | Applied AI, pilot champions, Product | - |
| Pilot pause or stop | Sponsor | Security, Product, pilot owner | - |
| Emergency kill switch activation | Any of: Security, SRE on-call, Product owner | Notify sponsor within 1h | - |

The kill switch is deliberately available to more people than any other control. A control that requires a committee is not a safety control.

## 4. Communication plan

| Forum | Cadence | Audience | Purpose |
|---|---|---|---|
| Delivery standup | Daily | Core team | Blockers, progress |
| Product review | Weekly (Thu) | Product, engineering, pilot champions | Demo, feedback, priority |
| Security touchpoint | Weekly | Security, architect, integration | Emerging risk, access status |
| Gate review | End of each phase | Gate board | Go / conditional / hold |
| Sponsor update | Fortnightly | Sponsor, business owner | Progress, risk, decisions needed |
| Pilot user channel | Continuous (Phases 5-6) | Pilot engineers, product, support | Support, feedback, failed-investigation review |
| RAID review | Weekly | Product lead + owners | Risk and issue movement |

## 5. Escalation path

1. Team-level blocker → Product owner (same day)
2. Cross-team or access blocker → Product owner + relevant lead (24h)
3. Gate-threatening issue → Sponsor (48h)
4. Security incident or suspected unauthorized access → **Security lead immediately**, kill switch first, investigate second
5. Any observed production write attempt → **Immediate stop**, sponsor and security notified within the hour

## 6. Sign-off

| Role | Name | Confirms | Date |
|---|---|---|---|
| Product lead | | Register and RACI accurate | |
| Executive sponsor | | Decision rights accepted | |
| Pilot team owner | | Team commitments accepted | |
