# 09 - Success Criteria and Pilot Scorecard

> **Status:** Derived targets awaiting baselining and ratification | **Owner:** Product lead | **Due:** Thursday 10 September 2026
> **Decision required at Gate 0:** ratify or amend every target below

---

## 1. Principle

Usage is not success. The proposal is explicit: the product must improve a real reliability outcome without weakening control. The scorecard therefore has four independent dimensions, and **all four must pass** for an unconditional Gate 6 go. A pilot that is fast and popular but leaks data fails. A pilot that is perfectly governed and produces useless diagnoses also fails.

Every target below is a **hypothesis to validate**, not a commitment. Several cannot be set responsibly by the build team - they are marked for sponsor ratification.

## 2. Dimension 1 - Speed

| ID | Measure | Baseline | Target | Method | Owner |
|---|---|---|---|---|---|
| SC-01 | Time to first useful diagnosis (p50) | B-01 `<<FILL>>` | **< 5 min** | Investigation timestamps + usefulness adjudication | Product |
| SC-02 | Time to first useful diagnosis (p95) | B-03 `<<FILL>>` | < 5 min (hard budget, SDD 9.6) | Telemetry | Platform |
| SC-03 | Reduction in median human triage time | B-01 `<<FILL>>` | **>= 50%** | Before/after on selected pipelines | Product |
| SC-04 | Initial acknowledgement latency | n/a | <= 2 s | API telemetry | Platform |
| SC-05 | Evidence-collection time eliminated | B-07 `<<FILL>>` | `<<FILL: derive from 05 | Product | Thu 10 Sep>>` | Workflow comparison | Product |

**Caveat to state at Gate 0:** SC-03 is only achievable if the steps NEXUS automates represent a majority of current elapsed triage time. Document [05](05_Current_State_Incident_Workflow.md) section 6 tests this. If evidence collection is (say) 30% of elapsed time, a 50% total reduction is arithmetically impossible and the target must be restated as a reduction in the addressable segment.

## 3. Dimension 2 - Quality

| ID | Measure | Target | Method | Owner |
|---|---|---|---|---|
| SC-06 | Material claims linked to inspectable evidence | **>= 90%** | Evaluator metric + audit sample | Applied AI |
| SC-07 | Root-cause accuracy, top-1 | >= 60% `<<ratify>>` | Golden set | Applied AI |
| SC-08 | Root-cause accuracy, top-3 | >= 80% `<<ratify>>` | Golden set | Applied AI |
| SC-09 | Hallucination rate (claims contradicted by evidence) | **0** in the critical class | Golden set + adversarial subset | Applied AI |
| SC-10 | Calibration - precision of High-confidence claims | >= 85% `<<ratify>>` | Golden set | Applied AI |
| SC-11 | Appropriate abstention on under-evidenced cases | >= 70% `<<ratify>>` | Designed-insufficient subset | Applied AI |
| SC-12 | Consistency - same incident, 3 runs, same top hypothesis | >= 80% | Repeat runs | Applied AI |
| SC-13 | Evidence coverage - required artifacts actually retrieved | `<<FILL: set from golden set labels>>` | Golden set | Applied AI |

SC-07, SC-08, SC-10 and SC-11 **cannot be derived from the source documents** and must be set by the sponsor with the applied AI lead and pilot champions at Gate 0. The values shown are the SDD's proposals, offered as a starting point.

SC-11 deserves emphasis: a system that never abstains is not calibrated, it is merely confident. Abstention is scored as a success, not a failure.

## 4. Dimension 3 - Trust and control

| ID | Measure | Target | Method | Owner |
|---|---|---|---|---|
| SC-14 | Tool calls policy-checked and audited | **100%** | Audit completeness metric | Security |
| SC-15 | Unauthorized production write actions | **0** | Architectural absence + security test | Security |
| SC-16 | Unauthorized data reaching a user or the model | **0** | Authz test suite + audit review | Security |
| SC-17 | Unresolved critical security findings | **0** | Security review | Security |
| SC-18 | Cross-user / cross-team isolation tests | 100% pass | CI + Phase 4 suite | Security |
| SC-19 | Secrets exposed in prompts, responses, or logs | **0** | Scanning + test suite | Security |
| SC-20 | Audit trail reconstructable per incident (US-08) | 100% | Auditor walkthrough | Security / Audit |

These are pass/fail, not scored. Any non-zero result on SC-15, SC-16, or SC-19 pauses the pilot.

## 5. Dimension 4 - Adoption and economics

| ID | Measure | Baseline | Target | Method | Owner |
|---|---|---|---|---|---|
| SC-21 | Pilot-user usefulness rating | n/a | `<<FILL: threshold agreed before pilot | Sponsor | Fri 11 Sep>>` | In-product feedback | Product |
| SC-22 | Pilot engineers completing an investigation unaided | n/a | 100% of pilot users | Pilot observation | Product |
| SC-23 | Investigations per pilot user per week | n/a | `<<FILL>>` | Product analytics | Product |
| SC-24 | Repeat usage (users returning after first use) | n/a | `<<FILL>>` | Product analytics | Product |
| SC-25 | Escalation rate reduction | B-11 `<<FILL>>` | `<<FILL>>` | Before/after | Operations |
| SC-26 | **Cost per useful diagnosis** | n/a | `<<FILL: ceiling | Sponsor | Fri 11 Sep>>` | Model + infra spend / useful diagnoses | Product + Platform |
| SC-27 | Direct monthly productivity value | B-13/B-22 | `<<FILL>>` | Value model, document 06 | Product |
| SC-28 | Value versus run cost | n/a | Positive with a stated payback period | Cost model, Phase 6 | Sponsor |

SC-26 is the metric that decides whether this scales. It is instrumented from Phase 1 (SDD 12) so it is measured throughout, not reconstructed in Week 12.

## 6. Pilot scorecard (completed at Gate 6)

| Dimension | Weight | Result | Pass? |
|---|---|---|---|
| Speed (SC-01..05) | Must pass SC-01, SC-03 | | |
| Quality (SC-06..13) | Must pass SC-06, SC-09 | | |
| Trust and control (SC-14..20) | **All must pass** | | |
| Adoption and economics (SC-21..28) | Must pass SC-21, SC-28 | | |

## 7. Decision rule

Carried forward from the proposal, with the conditional outcomes made explicit:

| Outcome | Condition | Action |
|---|---|---|
| **Scale** | Speed and quality targets met; all control gates pass; economics positive | Proceed to production; open the Phase 7 gate discussion |
| **Conditional go** | Targets met but with a named remediable gap | Production with conditions and a dated remediation plan |
| **Extend pilot** | Direction is right, evidence insufficient (e.g. too few incidents in the window) | Extend with a defined additional measurement period |
| **Pause** | Access or evidence controls unreliable | Halt build; remediate controls; re-gate |
| **Stop** | Value not demonstrable, or economics negative with no credible path | Stop; publish what was learned |
| **Redesign** | Any request to enable a write action | New gate, new threat model, new approval - never an extension of this pilot's authority |

## 8. Anti-gaming provisions

Agreed now, when nobody has an interest in the outcome:

1. **Usefulness is adjudicated by pilot engineers, not the build team.**
2. **The evaluation golden set is frozen before Phase 3 tuning begins** and is not used to select prompts. A separate development set is used for iteration.
3. **The baseline is sampled randomly** (document 06 section 4), not chosen from memorable incidents.
4. **Failed and abstained investigations are reported**, not filtered out of the results.
5. **Incidents where NEXUS was not used are counted** in the adoption denominator.
6. **The Gate 6 report states the incident count.** A 50% improvement over four incidents is an anecdote.

## 9. Ratification

| Item | Ratified value | Sponsor | Date |
|---|---|---|---|
| SC-07 root-cause top-1 target | | | |
| SC-08 root-cause top-3 target | | | |
| SC-10 calibration target | | | |
| SC-11 abstention target | | | |
| SC-21 usefulness threshold | | | |
| SC-26 cost-per-diagnosis ceiling | | | |
| SC-03 triage-reduction target (after 05 section 6 analysis) | | | |
