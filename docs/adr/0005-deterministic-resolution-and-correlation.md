# ADR-0005: Deterministic resolution, diffing and correlation

**Status:** Accepted  
**Date:** 2026-09-07  
**Deciders:** Technical architect  
**Supersedes:** none

## Context

Pipeline resolution, run comparison, schema diffing and volume deltas are all
exactly computable. Asking a model to do them introduces a hallucination surface
and a per-token cost for work that arithmetic does correctly and for free.

## Decision

Resolution, comparison, diffing and timeline merging are implemented as code.
The model classifies, correlates and explains. It does not compute or look up.

Ambiguity in resolution escalates to the user with candidate options rather than
being guessed.

## Consequences

- A whole class of wrong answers becomes impossible rather than unlikely.
- Cost and latency drop, because the expensive component does less work.
- More engineering effort up front, in exchange for outputs that are stable
  across runs - which the consistency criterion requires.

## References

- `NEXUS_Solution_Design_Document_v1.0.md`
- `NEXUS_Project_Phases_and_Delivery_Plan_v1.0.md`
