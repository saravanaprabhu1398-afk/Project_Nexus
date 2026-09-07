# ADR-0008: Evaluation harness precedes reasoning work

**Status:** Accepted  
**Date:** 2026-09-07  
**Deciders:** Technical architect  
**Supersedes:** none

## Context

Gate 3 asks whether the diagnosis is useful enough to justify enterprise
hardening, and the delivery plan requires that be answered by an evaluation
suite rather than demonstrations.

## Decision

The golden incident set and the harness that scores against it are built before
the reasoning they grade. The golden set is frozen before tuning begins, and a
separate development set is used for iteration.

Labelling starts in Week 1, not in Phase 3.

## Consequences

- Gate 3 has evidence instead of a demo.
- Tuning cannot overfit the set it is graded on.
- Labelling is 20-35 engineer-hours from people not otherwise allocated to the
  programme. It is tracked as the highest-scoring risk in the RAID log.

## References

- `NEXUS_Solution_Design_Document_v1.0.md`
- `NEXUS_Project_Phases_and_Delivery_Plan_v1.0.md`
