# ADR-0004: Normalized evidence envelope at the gateway boundary

**Status:** Accepted  
**Date:** 2026-09-07  
**Deciders:** Technical architect  
**Supersedes:** none

## Context

Platform independence is a stated principle: Databricks is Tool #1, not the
architectural boundary. Principles of that kind decay unless something enforces
them.

## Decision

Connectors return `Evidence`, never provider-native objects. No module above the
tool gateway may reference a provider-specific field name. A Databricks task
failure and, later, an Airflow task failure both normalize to
`evidence_type = task_error` with the same envelope.

## Consequences

- Phase 10 integrations implement tools and mappings rather than touching the
  runtime.
- Some provider detail is lost at the boundary. The raw payload is retained
  separately, under its own shorter retention, for cases that need it.
- Enforcement is a lint rule plus a contract test, not a code review habit.

## References

- `NEXUS_Solution_Design_Document_v1.0.md`
- `NEXUS_Project_Phases_and_Delivery_Plan_v1.0.md`
