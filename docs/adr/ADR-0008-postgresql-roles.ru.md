<!-- ru-translation-of: docs/adr/ADR-0008-postgresql-roles.md sha:acd007a65d01 -->
<!-- Автоперевод. Источник — docs/adr/ADR-0008-postgresql-roles.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0008-postgresql-roles.md](ADR-0008-postgresql-roles.md)

# ADR-0008 — Роли PostgreSQL: landing + platform_meta + бэкенд Prefect

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D9/D11 · [ADR-0006](ADR-0006-dlt-default-ingestion-postgres-landing.md)

## Context

PostgreSQL входит в объявленный стек. Это неправильный движок для OLAP-сканов (за это отвечает DuckDB), но правильный для буферизации в стиле OLTP и метаданных.

## Decision

Используем один PostgreSQL для трёх ролей: (1) схема **`landing`** — надёжное промежуточное хранилище для собранных/распарсенных данных до того, как dlt/ingestr загрузят их; (2) **`platform_meta`** — статистика запусков, watermark-и, результаты DQ; (3) **бэкенд сервера Prefect** (когда включён профиль `server`).

## Consequences

- Чёткое разделение хранилища (объектное хранилище), вычислений (DuckDB) и OLTP/метаданных (Postgres).
- Ещё один сервис для запуска; держится в основном compose, единственным экземпляром.

## Alternatives considered

- **SQLite для метаданных** — слишком ограничен для бэкенда Prefect + конкурентных записей в landing.
- **Postgres как хранилище** — отклонено ([ADR-0002](ADR-0002-duckdb-analytical-engine.md)).
