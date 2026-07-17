# ADR-0007 — Prefect 3 orchestration + runnable alternative setups

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D1/D3 · [ADR-0004](ADR-0004-sqlmesh-default-transform-engine.md)

## Context

The platform needs Pythonic, local-first orchestration with no heavy control plane, plus an
honest demonstration of alternative orchestrator/engine stacks.

## Decision

**Prefect 3** orchestrates the production flow (`ingest → transform → dq → publish_outputs`),
ephemeral by default with a `server` profile (+ Postgres) optional. Alternative **complete,
runnable** setups live in `experimental/orchestration/`: **Prefect+Bruin** and
**Prefect+Dagster-over-dlt/dbt** (plus `prefect-dbt`, `prefect-sqlmesh-over-dbt`), all consuming
the same `spec/` via `just run-profile <name>`.

## Consequences

- One production orchestrator; alternatives are demonstrable but never on the prod path.
- Profile matrix must stay in sync with the spec compiler.

## Alternatives considered

- **Dagster as the sole orchestrator** — kept as a complete alt setup, not the default.
- **Airflow** — heavier control plane; not local-first.
