<!-- ru-translation-of: docs/adr/ADR-0007-prefect-orchestration.md sha:59dc5727c5f2 -->
<!-- Автоперевод. Источник — docs/adr/ADR-0007-prefect-orchestration.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0007-prefect-orchestration.md](ADR-0007-prefect-orchestration.md)

# ADR-0007 — Оркестрация на Prefect 3 + запускаемые альтернативные конфигурации

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D1/D3 · [ADR-0004](ADR-0004-sqlmesh-default-transform-engine.md)

## Context

Платформе нужна питоническая, local-first оркестрация без тяжёлого control plane, а также
честная демонстрация альтернативных стеков оркестраторов и движков.

## Decision

**Prefect 3** оркестрирует production-поток (`ingest → transform → dq → publish_outputs`),
эфемерный по умолчанию с опциональным профилем `server` (+ Postgres). Альтернативные
**полные, запускаемые** конфигурации живут в `experimental/orchestration/`: **Prefect+Bruin** и
**Prefect+Dagster-over-dlt/dbt** (плюс `prefect-dbt`, `prefect-sqlmesh-over-dbt`), все потребляют
один и тот же `spec/` через `just run-profile <name>`.

## Consequences

- Один production-оркестратор; альтернативы демонстрируемы, но никогда не на prod-пути.
- Матрица профилей должна оставаться синхронизированной с компилятором спецификации.

## Alternatives considered

- **Dagster как единственный оркестратор** — оставлен как полноценная альтернативная конфигурация, а не как значение по умолчанию.
- **Airflow** — более тяжёлый control plane; не local-first.
