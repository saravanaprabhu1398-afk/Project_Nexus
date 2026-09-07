# Architecture Decision Records

One record per decision that was genuinely contested or that a future reader
would otherwise be tempted to reverse. Each states the context that forced the
choice, so a change of context is visible as a reason to revisit it.

Eight of these close inconsistencies found between the approved proposal and the
delivery plan; those carry the finding reference (A-n) in their context section.

| ADR | Decision | Phase |
|---|---|---|
| [ADR-0001](0001-asynchronous-investigation-api.md) | Asynchronous investigation API | 1 |
| [ADR-0002](0002-single-deployable-service.md) | Single deployable service, service-shaped modules | 1 |
| [ADR-0003](0003-policy-decision-point-from-phase-1.md) | Policy decision point in the call path from Phase 1 | 1 |
| [ADR-0004](0004-normalized-evidence-envelope.md) | Normalized evidence envelope at the gateway boundary | 2 |
| [ADR-0005](0005-deterministic-resolution-and-correlation.md) | Deterministic resolution, diffing and correlation | 2-3 |
| [ADR-0006](0006-banded-confidence.md) | Banded confidence, not numeric | 3 |
| [ADR-0007](0007-user-delegation-identity.md) | User delegation as the primary identity model | 4 |
| [ADR-0008](0008-evaluation-before-tuning.md) | Evaluation harness precedes reasoning work | 3 |
| [ADR-0009](0009-untrusted-content-quarantine.md) | Quarantine untrusted tool output before it reaches a prompt | 3 |
| [ADR-0010](0010-tenant-partitioning-from-first-migration.md) | Tenant partitioning from the first migration | 1 |
| [ADR-0011](0011-retention-ships-with-storage.md) | Retention and its purge job ship with the store | 2 |

## Writing a new one

Copy the shape above: Context, Decision, Consequences. Record the consequences
that are costs, not only the ones that are benefits - a record listing only
advantages is advocacy, and it gives a later reader nothing to weigh.

Number sequentially. Supersede rather than edit: the reasoning that was true at
the time is what makes the history worth keeping.
