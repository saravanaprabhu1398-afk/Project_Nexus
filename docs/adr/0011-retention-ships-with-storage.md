# ADR-0011: Retention and its purge job ship with the store

**Status:** Accepted  
**Date:** 2026-09-07  
**Deciders:** Technical architect  
**Supersedes:** none

## Context

Phase 2 begins persisting raw tool payloads while retention was still an open
decision, D-07 (finding A-9). Building a store without a delete path is the
clearest irreversible mistake available to this programme.

## Decision

Every table holding retrievable content carries `expires_at`, set at creation.
A purge job with a passing test ships in the same increment as the first write.
Audit records are excluded: their removal is a separate privileged process, not
routine purging.

## Consequences

- Gate 2 evidence can include a demonstration that an expired record is gone.
- Retention values remain a privacy decision; the mechanism does not wait for
  the values to be ratified.
- Deleting an investigation retains the audit record describing the deletion,
  so deletion itself stays auditable.

## References

- `NEXUS_Solution_Design_Document_v1.0.md`
- `NEXUS_Project_Phases_and_Delivery_Plan_v1.0.md`
