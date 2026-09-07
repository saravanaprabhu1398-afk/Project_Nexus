# ADR-0002: Single deployable service, service-shaped modules

**Status:** Accepted  
**Date:** 2026-09-07  
**Deciders:** Technical architect  
**Supersedes:** none

## Context

The reference architecture names five layers and a dozen components. Splitting
those into separate services now would fix boundaries before the load
characteristics that should determine them are known.

## Decision

Ship one deployable service. Draw module boundaries as if they were service
boundaries: no shared mutable state, contract-typed calls across them, and no
module above the tool gateway referencing a provider-specific type.

## Consequences

- Operational cost stays low while the product is unproven.
- Extraction in Phase 8-10 is mechanical rather than a rewrite, because the
  seams already exist.
- Discipline is required: a shortcut across a module boundary is cheap now and
  expensive later. The lint rule and contract test on the evidence envelope
  exist to make one class of shortcut fail in CI.

## References

- `NEXUS_Solution_Design_Document_v1.0.md`
- `NEXUS_Project_Phases_and_Delivery_Plan_v1.0.md`
