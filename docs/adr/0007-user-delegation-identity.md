# ADR-0007: User delegation as the primary identity model

**Status:** Accepted  
**Date:** 2026-09-07  
**Deciders:** Technical architect  
**Supersedes:** none

## Context

Open decision D-03 asks whether the agent acts with the invoking user's
permissions, a service identity, or a hybrid. A service identity is simpler and
is the more common default.

## Decision

User delegation is primary: the agent reads with the invoking engineer's own
effective permissions wherever the platform supports it. A narrow service
identity is used only for genuinely shared resources such as the runbook index,
and its scope must be narrower than the union of pilot users' scopes.

## Consequences

- The agent can never surface data the requesting person could not have
  retrieved themselves. This is the property that makes the aggregation of many
  sources into one view defensible.
- Some platforms may not support delegation; where they do not, every access is
  authorization-checked against the user before the result is returned.
- Debugging is harder, because a failure may be the user's permissions rather
  than the system's.

## References

- `NEXUS_Solution_Design_Document_v1.0.md`
- `NEXUS_Project_Phases_and_Delivery_Plan_v1.0.md`
