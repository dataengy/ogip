# ADR-0003 — Parquet lake; defer Iceberg/DuckLake

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** [ADR-0002](ADR-0002-duckdb-analytical-engine.md) · `docs/comparisons/iceberg-vs-ducklake.md`

## Context

The raw lake needs an open, columnar format. Table formats (Iceberg, DuckLake) add ACID,
snapshots, and multi-engine reads — but also a catalog to operate.

## Decision

Use **plain Parquet** (via PyArrow) on local FS (dev default) / **Cloudflare R2** (cloud of
record), S3-API code paths identical (MinIO/S3 profiles). Table formats stay a **research
track** (`iceberg-vs-ducklake.md`), adopted only when concurrency/time-travel/multi-engine
reads become product requirements.

## Consequences

- Zero catalog to operate; fork-and-run stays trivial.
- No table-level ACID/time-travel until a documented migration is triggered.

## Alternatives considered

- **Iceberg / DuckLake as default** (OGAP's ADR-022) — reverted: adds a catalog and ops burden not yet justified.
