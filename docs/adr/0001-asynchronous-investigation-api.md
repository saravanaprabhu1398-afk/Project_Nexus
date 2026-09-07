# ADR-0001: Asynchronous investigation API

**Status:** Accepted  
**Date:** 2026-09-07  
**Deciders:** Technical architect  
**Supersedes:** none

## Context

The PRD sets two latency targets: acknowledge a request within 2 seconds, and
produce a useful diagnosis within 5 minutes. A synchronous request cannot meet
both. Reviewing the proposal against the delivery plan surfaced this as finding
A-6.

## Decision

`POST /v1/investigations` validates, persists the investigation record, returns
`202` with a `Location` header, and executes the work afterwards. Callers poll
`GET /v1/investigations/{id}` or subscribe to the event stream.

## Consequences

- Both latency targets are meetable, and they measure different things: the
  acknowledgement is an API property, the diagnosis is a pipeline property.
- Partial results are naturally expressible, which the resilience requirement
  needs anyway.
- Clients must handle a non-terminal state. The status enum is explicit about
  which states are terminal.
- Investigation execution must survive process restart. Trace steps are
  persisted as the work proceeds so a crashed investigation is recoverable
  rather than lost.

## References

- `NEXUS_Solution_Design_Document_v1.0.md`
- `NEXUS_Project_Phases_and_Delivery_Plan_v1.0.md`
