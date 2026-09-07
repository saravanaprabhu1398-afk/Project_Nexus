# 08 - Data Classification and Retention Constraints

> **Status:** Derived proposal + privacy approval | **Owner:** Data privacy / compliance (with Security) | **Due:** Thursday 10 September 2026
> **Closes:** open decision D-07 (retention), contributes to D-02 (residency) and D-04 (knowledge scope)

---

## 1. Why this cannot wait for Phase 4

Phase 2 begins persisting raw tool payloads in Week 4. Building a store without a delete path is the programme's clearest irreversible mistake (SDD finding A-9), and retention rules are cheap to implement in Week 4 and expensive to retrofit in Week 9. This document therefore proposes concrete defaults now, for privacy to ratify or amend at Gate 0.

## 2. Classification scheme

| Tier | Definition | Handling in NEXUS |
|---|---|---|
| **Public** | No harm if disclosed | No restriction |
| **Internal** | Routine business data | Default tier; tenant-scoped access |
| **Confidential** | Harmful if disclosed outside a need-to-know group | Access logged; redaction applied; not used in prompts unless required for the diagnosis |
| **Restricted** | Regulated, personal, or secret | **Not retrieved by NEXUS in the MVP.** If encountered incidentally (e.g. in a log line) it is redacted before persistence and before model input |

## 3. Data inventory and classification

| Data class | Example | Proposed tier | In model context? | Persisted? | Retention |
|---|---|---|---|---|---|
| Job / run metadata | Job ID, run state, timings | Internal | Yes | Yes | 90 days |
| Job / cluster configuration | Spark conf, libraries, instance type | Internal | Yes | Yes | 90 days |
| Task error and stack trace | Exception text | **Confidential** (may contain data values) | Yes, **after redaction** | Yes, redacted | 90 days |
| Driver / task log excerpt | Log lines around the failure | **Confidential** | Windowed + redacted excerpt only | Excerpt only | 30 days |
| Raw tool payload | Unnormalized API response | Confidential | **No** | Yes, separate store | **30 days, purge job in Phase 2** |
| Catalog schema metadata | Column names, types | Internal | Yes | Yes | 90 days |
| Lineage | Table relationships | Internal / Confidential | Yes | Yes | 90 days |
| Table statistics | Row counts, sizes | Internal | Yes | Yes | 90 days |
| **Table data values** | Actual rows | Restricted | **No - not retrieved in MVP** | No | n/a |
| Runbook content | Operational docs | Internal | Yes | Indexed | Until source withdrawn |
| Historical incident records | Ticket text | Internal / Confidential | Yes, redacted | Indexed | Until source withdrawn |
| Repository metadata (conditional) | Commit message, author, files changed | Internal | Yes | Yes | 90 days |
| **Repository source content** | Code | Confidential | **No - not retrieved in MVP** | No | n/a |
| User question text | Free text from an engineer | Internal | Yes | Yes | 1 year (trace) |
| Investigation trace | Plan, tool calls, observations | Internal | n/a | Yes, **immutable** | 1 year |
| Diagnosis output | Hypotheses, citations, recommendation | Internal | n/a | Yes | 1 year |
| Audit records | Who accessed what, why, decision | **Confidential** | **No** | Yes, **append-only** | 1 year minimum, subject to audit policy |
| User feedback | Rating, actual root cause | Internal | Yes (evaluation) | Yes | 1 year |
| Model prompts and completions | Full context sent to provider | Confidential | n/a | Hash + metadata only by default | 30 days if stored |
| Secrets and credentials | Tokens, keys | **Restricted** | **Never** | **Never** | n/a |

`<<FILL: privacy review of proposed tiers and retention | Data privacy | Thu 10 Sep>>`

## 4. Retention summary and enforcement

| Store | Retention | Enforcement | Ships in |
|---|---|---|---|
| Raw payload store | 30 days | Scheduled purge job + `expires_at` on every row | **Phase 2** |
| Evidence (normalized, redacted) | 90 days | `expires_at` + purge job | Phase 2 |
| Operational facts | 90 days | Purge job | Phase 2 |
| Log excerpts | 30 days | Purge job | Phase 2 |
| Agent trace | 1 year | Purge job; **no UPDATE/DELETE grant to the app role** before expiry | Phase 2 |
| Audit records | 1 year+ | Append-only; deletion requires a separate privileged process | Phase 1 |
| Knowledge index | Until source withdrawn | Re-index on source change; delete on withdrawal | Phase 3 |
| Model prompt bodies | Not stored by default | Hash + token counts only; full capture behind an explicit debug flag with 7-day expiry | Phase 1 |

**The purge job is a Phase 2 deliverable with a test, not a Phase 6 clean-up task.** Gate 2 evidence must include a demonstration that a record past its retention date is actually gone.

## 5. Redaction requirements

Two-stage, applied at the tool gateway before persistence and before model input (SDD 10.3):

**Stage 1 - structural.** Drop known-sensitive fields per connector (credentials, tokens, connection strings, environment variables, instance profile ARNs, user emails where not needed for routing).

**Stage 2 - pattern.** Applied to free text, principally log lines and stack traces:

| Pattern class | Action |
|---|---|
| Credentials, API keys, bearer tokens | Redact |
| High-entropy strings above a threshold | Redact, flag for review |
| Connection strings and URLs with embedded auth | Redact auth component |
| Email addresses, phone numbers, national IDs | Redact |
| Payment card patterns | Redact |
| Customer identifiers (domain-specific) | `<<FILL: define patterns for this domain | Data privacy + Data eng | Thu 10 Sep>>` |
| IP addresses | `<<FILL: redact or retain - decide>>` |
| File paths containing user or customer names | `<<FILL: decide>>` |

`redaction_applied` is recorded on the evidence row so an auditor can confirm redaction occurred without viewing the content. Redaction is measured for false negatives in the security test suite - a redaction filter nobody tests is decoration.

## 6. Residency and processing location (D-02)

| Question | Answer |
|---|---|
| Where does the agent runtime execute? | `<<FILL>>` |
| Where do Postgres, Redis, vector store, object store reside? | `<<FILL>>` |
| Where is the model endpoint hosted? | `<<FILL>>` |
| Does any data cross a regional or legal boundary? | `<<FILL>>` |
| Where do traces and telemetry land, and does that export content? | `<<FILL - telemetry is a common accidental egress path>>` |
| Applicable regimes (GDPR, sector-specific, internal policy) | `<<FILL>>` |

**Recommendation:** co-locate runtime, all state stores, and the model endpoint in the pilot's data region, and configure telemetry to export metrics and span metadata but never span content.

## 7. Model provider data handling (D-06)

| Requirement | Status |
|---|---|
| Prompt data not used for training | `<<FILL: must be contractually confirmed by Gate 1>>` |
| Provider-side retention period | `<<FILL>>` |
| Zero/short data-retention option available | `<<FILL>>` |
| Processing region controllable | `<<FILL>>` |
| Subprocessor list reviewed | `<<FILL>>` |
| Contract or DPA in place | `<<FILL>>` |

If no-training terms cannot be confirmed by Gate 1, the fallback is a self-hosted or in-tenant model endpoint, which changes the cost model and must be raised as a risk now rather than at Gate 4.

## 8. Deletion and subject rights

| Requirement | Implementation |
|---|---|
| Delete a single investigation | API-supported; cascades to evidence, trace, and payloads; audit record of the deletion retained |
| Delete a user's investigation history | Supported by subject-scoped query |
| Withdraw a knowledge source | Delete from index and vector store; re-index on next run |
| Legal hold | Suspends purge for the flagged records; documented process |
| Right-to-erasure requests | `<<FILL: is any personal data in scope? | Data privacy | Thu 10 Sep>>` |

An audit record documenting a deletion is retained even when the underlying data is removed - otherwise deletion itself becomes unauditable.

## 9. Sign-off

| Role | Name | Confirms | Date |
|---|---|---|---|
| Data privacy / compliance | | Classification and retention approved | |
| Security engineer | | Redaction and controls sufficient | |
| Legal (if required) | | Residency and provider terms acceptable | |
| Technical architect | | Implementable as specified in Phase 2 | |
