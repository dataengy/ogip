# ADR-0006 — dlt default ingestion + Postgres landing; ingestr optional (CDC)

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D11 · [ADR-0008](ADR-0008-postgresql-roles.md) · `docs/comparisons/dlt-vs-ingestr.md`

## Context

Several target APIs are hostile/undocumented (Steam limits, IGDB OAuth2, HLTB/Metacritic
scraping). Scraped/parsed data is messy and benefits from a durable, queryable buffer before
it becomes an immutable raw record.

## Decision

**dlt** is the default ingestion engine (via a `BaseSource` family). Two patterns: clean APIs
go **dlt-direct** → raw Parquet; scraped/parsed data lands in a **PostgreSQL `landing`** schema
first, then **dlt** (default) — or **ingestr** (optional, for CDC) — loads it to raw Parquet.

## Consequences

- Retries/reprocessing of scraped data are cheap; the load step gets a clean, typed source.
- ingestr/CDC available for future near-real-time capture without re-architecting.

## Alternatives considered

- **Airbyte as primary** — reverted: low-code connectors don't fit hostile APIs; removed from core.
- **ingestr as default** — kept optional; dlt gives more Python control for custom sources.
