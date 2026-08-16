<!-- ru-translation-of: docs/adr/ADR-0004-sqlmesh-default-transform-engine.md sha:367950ff8ed3 -->
<!-- Автоперевод. Источник — docs/adr/ADR-0004-sqlmesh-default-transform-engine.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0004-sqlmesh-default-transform-engine.md](ADR-0004-sqlmesh-default-transform-engine.md)

# ADR-0004 — SQLMesh как движок трансформаций по умолчанию

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D5 · [ADR-0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md), [ADR-0007](ADR-0007-prefect-orchestration.md)

## Context

Трансформациям нужны безопасные развёртывания, упорядочивание зависимостей и происхождение
данных на уровне столбцов без поднятия отдельного сервера. dbt, Bruin и простой SQL-раннер
жизнеспособны, но различаются по безопасности и происхождению.

## Decision

Использовать **SQLMesh** как движок продакшн-трансформаций по умолчанию (компилируется из `spec/`,
выполняется на DuckDB, упорядочивается Prefect). Механизмы plan/apply в SQLMesh, виртуальные
среды данных и происхождение на уровне столбцов дают безопасные, пригодные к ревью развёртывания
без дополнительного сервиса.

## Consequences

- Безопасное продвижение в стиле blue/green и анализ влияния при каждом изменении.
- Требует шага компиляции spec→SQLMesh ([ADR-0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md)).
- Простой SQL-раннер, dbt и Bruin остаются **запускаемыми для сравнения** движками в `experimental/`.

## Alternatives considered

- **dbt** — крупнейшая экосистема, но более слабое нативное происхождение/безопасное развёртывание; сохранён как сравнение + профиль Dagster.
- **Plain-SQL runner** — самый простой, но без происхождения/plan-apply; сохранён как сравнение.
