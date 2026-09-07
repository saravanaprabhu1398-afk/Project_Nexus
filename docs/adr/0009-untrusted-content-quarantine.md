# ADR-0009: Quarantine untrusted tool output before it reaches a prompt

**Status:** Accepted  
**Date:** 2026-09-07  
**Deciders:** Technical architect  
**Supersedes:** none

## Context

Logs, task output, runbooks and ticket text are all attacker-influenceable and
are ingested from Phase 3. The plan placed injection defence in Phase 4, after
the exposure it defends against (finding A-8).

## Decision

Untrusted content enters a prompt only inside a delimited block carrying a
standing instruction that its contents are data, never instruction. Tool
selection comes from the registry only, so a tool name appearing in tool output
can never cause an invocation. Output is scanned for instruction-like directives
and for URLs not present in cited evidence.

## Consequences

- The defence precedes the exposure rather than following it.
- The capability floor is what makes a successful injection survivable: with no
  write-capable tool in the registry, the worst outcome is a wasted budget or a
  wrong but citation-bound claim.
- Phase 4 adds adversarial testing and formal review on top, rather than
  introducing the control.

## References

- `NEXUS_Solution_Design_Document_v1.0.md`
- `NEXUS_Project_Phases_and_Delivery_Plan_v1.0.md`
