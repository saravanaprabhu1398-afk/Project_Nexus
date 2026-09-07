# ADR-0006: Banded confidence, not numeric

**Status:** Accepted  
**Date:** 2026-09-07  
**Deciders:** Technical architect  
**Supersedes:** none

## Context

The product mock displays "Confidence 0.92". No phase of the plan delivers a
calibration method that would make such a figure meaningful (finding A-7).

## Decision

Confidence is reported as High, Medium, Low or Abstain, against published
criteria based on the presence of a direct causal artifact, independent
corroboration, and a matching known-failure pattern.

Abstention is a success path, and it is measured.

## Consequences

- The reported confidence can actually be validated: precision within the High
  band is measurable against the evaluation set.
- Unearned precision is avoided. A decimal invites trust the system has not
  earned, which works directly against the product's central goal.
- A system that never abstains is visibly uncalibrated rather than
  reassuringly confident.

## References

- `NEXUS_Solution_Design_Document_v1.0.md`
- `NEXUS_Project_Phases_and_Delivery_Plan_v1.0.md`
