# ADR-0003: Policy decision point in the call path from Phase 1

**Status:** Accepted  
**Date:** 2026-09-07  
**Deciders:** Technical architect  
**Supersedes:** none

## Context

The PRD requires that 100% of tool calls are policy-checked and audited. That
applies from the first Databricks call in Phase 2. The policy engine, however,
is a Phase 4 deliverable. Taken literally, the plan would leave four weeks of
unchecked tool calls (finding A-2).

## Decision

Build the decision interface, the decision token and the audit sink in Phase 1,
with a deny-by-default static allowlist behind them. Phase 4 replaces the
implementation, never the call path.

The gateway exposes exactly one entry point and requires a decision with
`effect=PERMIT` whose binding hash matches the exact
`(subject, tool, resource, investigation)` tuple and has not expired. There is
no bypass, no admin flag, and no test hook; tests exercise the production path.

## Consequences

- The 100% claim is true from the first real connector rather than from Week 9.
- Phase 4 is a substitution behind a stable interface, which is a much smaller
  and safer change than introducing enforcement into a working system.
- A decision cannot be reused across resources or investigations. This closes
  the confused-deputy escalation, and is covered by a test.

## References

- `NEXUS_Solution_Design_Document_v1.0.md`
- `NEXUS_Project_Phases_and_Delivery_Plan_v1.0.md`
