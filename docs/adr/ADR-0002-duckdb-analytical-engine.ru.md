<!-- ru-translation-of: docs/adr/ADR-0002-duckdb-analytical-engine.md sha:5c509f435702 -->
<!-- Автоперевод. Источник — docs/adr/ADR-0002-duckdb-analytical-engine.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0002-duckdb-analytical-engine.md](ADR-0002-duckdb-analytical-engine.md)

# ADR-0002 — DuckDB как аналитический движок

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** [ADR-0003](ADR-0003-parquet-lake-defer-iceberg-ducklake.md), [ADR-0004](ADR-0004-sqlmesh-default-transform-engine.md)

## Context

Платформа должна работать на ноутбуке и в CI на каждый PR, без каких-либо учётных записей, оставаясь при этом настоящим колоночным OLAP-движком.

## Decision

Используем **DuckDB** как аналитический/вычислительный движок. Он читает Parquet «на месте» (FS/S3/R2), работает внутри процесса и без операционной нагрузки, а всё хранилище — это единственный артефакт (`.run/data/warehouse/ogip.duckdb`), тривиально воспроизводимый и кешируемый в CI.

## Consequences

- Хранилище-в-CI обходится дёшево; полный transform-DAG выполняется на каждый PR.
- Потолок вычислений на одном узле; горизонтальное масштабирование — задача на будущее (задокументирована, но не решена).

## Alternatives considered

- **Postgres как хранилище** — неправильный движок для OLAP-сканов.
- **Управляемое хранилище (BigQuery/Snowflake)** — требует учётных записей; ломает сценарий fork-and-run.
