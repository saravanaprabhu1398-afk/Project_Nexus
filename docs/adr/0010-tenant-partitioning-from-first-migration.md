# ADR-0010: Tenant partitioning from the first migration

**Status:** Accepted  
**Date:** 2026-09-07  
**Deciders:** Technical architect  
**Supersedes:** none

## Context

Tenant appears in the normalized request contract and in the Phase 4 isolation
tests, but no tenancy model was specified (finding A-10).

## Decision

Every persisted row carries `tenant_id`, and it leads every composite index. No
repository exposes a query method without a `tenant_id` parameter, and writes
require the caller to state the tenant, which is validated against the row.

## Consequences

- Retrofitting tenancy after data exists would be a migration, not a change.
  Doing it now costs almost nothing.
- Cross-tenant tests run in CI from the first commit rather than only in the
  Phase 4 security suite - by Phase 4 the data model is already fixed.
- A guard test asserts the rule itself, so a convenience method that forgets the
  tenant fails in CI.

## References

- `NEXUS_Solution_Design_Document_v1.0.md`
- `NEXUS_Project_Phases_and_Delivery_Plan_v1.0.md`
