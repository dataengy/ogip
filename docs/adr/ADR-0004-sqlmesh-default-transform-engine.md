# ADR-0004 — SQLMesh as the default transform engine

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D5 · [ADR-0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md), [ADR-0007](ADR-0007-prefect-orchestration.md)

## Context

Transformations need safe deploys, dependency ordering, and column-level lineage without
standing up a separate server. dbt, Bruin, and a plain-SQL runner are viable but differ on
safety and lineage.

## Decision

Use **SQLMesh** as the default production transform engine (compiled from `spec/`, run on
DuckDB, sequenced by Prefect). SQLMesh's plan/apply, virtual data environments, and
column-level lineage give safe, reviewable deploys with no extra service.

## Consequences

- Safe blue/green-style promotion and impact analysis on every change.
- Requires a spec→SQLMesh compile step ([ADR-0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md)).
- Plain-SQL runner, dbt, and Bruin remain **runnable comparison** engines under `experimental/`.

## Alternatives considered

- **dbt** — largest ecosystem, but weaker native lineage/safe-deploy; kept as a comparison + Dagster profile.
- **Plain-SQL runner** — simplest, but no lineage/plan-apply; kept as a comparison.
