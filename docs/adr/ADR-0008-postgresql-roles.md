# ADR-0008 — PostgreSQL roles: landing + platform_meta + Prefect backend

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D9/D11 · [ADR-0006](ADR-0006-dlt-default-ingestion-postgres-landing.md)

## Context

PostgreSQL is in the declared stack. It's the wrong engine for OLAP scans (that's DuckDB), but
right for OLTP-style buffering and metadata.

## Decision

Use one PostgreSQL for three roles: (1) **`landing`** schema — durable intermediate for
scraped/parsed data before dlt/ingestr load it; (2) **`platform_meta`** — run stats,
watermarks, DQ results; (3) **Prefect server backend** (when the `server` profile is on).

## Consequences

- Clear separation of storage (object store), compute (DuckDB), and OLTP/metadata (Postgres).
- One more service to run; kept in the core compose, single instance.

## Alternatives considered

- **SQLite for metadata** — too limited for the Prefect backend + concurrent landing writes.
- **Postgres as the warehouse** — rejected ([ADR-0002](ADR-0002-duckdb-analytical-engine.md)).
