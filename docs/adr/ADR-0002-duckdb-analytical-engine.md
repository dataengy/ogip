# ADR-0002 — DuckDB as the analytical engine

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** [ADR-0003](ADR-0003-parquet-lake-defer-iceberg-ducklake.md), [ADR-0004](ADR-0004-sqlmesh-default-transform-engine.md)

## Context

The platform must run on a laptop and in CI on every PR, with zero accounts, while still
being a real columnar OLAP engine.

## Decision

Use **DuckDB** as the analytical/compute engine. It reads Parquet in place (FS/S3/R2),
is in-process and zero-ops, and the whole warehouse is a single artifact
(`.run/data/warehouse/ogip.duckdb`) — trivially reproducible and cacheable in CI.

## Consequences

- Warehouse-in-CI is cheap; the full transform DAG runs on every PR.
- Single-node compute ceiling; horizontal scale is a future concern (documented, not solved).

## Alternatives considered

- **Postgres-as-warehouse** — wrong engine for OLAP scans.
- **Hosted warehouse (BigQuery/Snowflake)** — needs accounts; breaks fork-and-run.
