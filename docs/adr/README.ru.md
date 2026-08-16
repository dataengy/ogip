<!-- ru-translation-of: docs/adr/README.md sha:b8fab57592f2 -->
<!-- Автоперевод. Источник — docs/adr/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# Записи архитектурных решений (ADR)

Зафиксированные во времени архитектурные решения OGIP. Одно решение на файл, неизменяемое после
статуса `Accepted` — вытесненные решения получают новый ADR со ссылкой на старый. Формат:
лёгкий [MADR](https://adr.github.io/madr/)/Nygard (Статус · Контекст · Решение ·
Последствия · Альтернативы). Для новых записей используйте [`_template.md`](_template.md).

Эти ADR формализуют зафиксированные решения части C (D0–D13) в [`.ai/PLAN.md`](../../.ai/PLAN.md).

| ADR | Название | Решение | Статус |
|---|---|---|---|
| [0001](ADR-0001-edw-layering-no-medallion.md) | Классическое EDW-слоение, без medallion | raw0 · stg · core · star · am · marts · fs | Accepted |
| [0002](ADR-0002-duckdb-analytical-engine.md) | DuckDB как аналитический движок | in-process OLAP, работает в CI | Accepted |
| [0003](ADR-0003-parquet-lake-defer-iceberg-ducklake.md) | Parquet-лейк; отложить Iceberg/DuckLake | Parquet на FS/R2; табличные форматы = исследование | Accepted |
| [0004](ADR-0004-sqlmesh-default-transform-engine.md) | SQLMesh как движок трансформаций по умолчанию | D5 | Accepted |
| [0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md) | SSoT `spec/`: Bruin + ODCS + компилятор | D0/D5 | Accepted |
| [0006](ADR-0006-dlt-default-ingestion-postgres-landing.md) | dlt как инжест по умолчанию + Postgres landing; ingestr CDC | D11 | Accepted |
| [0007](ADR-0007-prefect-orchestration.md) | Оркестрация Prefect 3 + запускаемые альт-сетапы | D1/D3 | Accepted |
| [0008](ADR-0008-postgresql-roles.md) | Роли PostgreSQL: landing + platform_meta + Prefect | D9 | Accepted |
| [0009](ADR-0009-ml-outputs-feature-store.md) | Продукт = ML-выходы + Feature Store; без BI/семантики в ядре | D6/D7/D8 | Accepted |
| [0010](ADR-0010-activity-model-layer.md) | Слой Activity Model (Activity Schema) | D13 | Accepted |
| [0011](ADR-0011-minimal-secrets.md) | Минимум секретов: `.env` + секреты GitHub Actions | D10 | Accepted |
| [0012](ADR-0012-github-ci-manual-vps-deploy.md) | CI на GitHub Actions + ручной деплой на VPS (DevOps отдельно) | D9 | Accepted |
| [0013](ADR-0013-github-issues-projects-tasks.md) | GitHub Issues/Projects как трекер задач | D12 | Accepted |
| [0014](ADR-0014-resilient-scraping-concurrency.md) | Устойчивый скрейпинг: async-first, effectively-once landing | паттерн скрейпера A6/D11 | Proposed |
| [0015](ADR-0015-dagster-alt-orchestration-dg-components.md) | Альт-оркестрация Dagster через `dg` Components (dbt + dlt + ingestr CDC) | альт-сетап ADR-0007, D1/D11 | Accepted |
| [0016](ADR-0016-odts-authoring-format-spec-sql.md) | Формат авторинга `@odts` для `spec/sql` | компактный заголовок · макросы · SQL-дисциплина; уточняет D0/D5 | Accepted |
| [0017](ADR-0017-odos-normative-profile.md) | Нормативный профиль оркестрации ODOS 0.1 | стандарт оркестрации (jobs/schedules/monitors), зонтик YADPS | Accepted |
| [0018](ADR-0018-odts-normative-profile.md) | Нормативный профиль трансформаций ODTS 0.1 | конформанс-фикстуры + тесты словаря | Accepted |
| [0019](ADR-0019-odts-dq-projection-and-seven-prefect-subprojects.md) | Проекция ODTS DQ в SQLMesh-аудиты + семь Prefect-подпроектов | `columns[].checks` → аудиты; флоу на каждый движок | Accepted |
| [0020](ADR-0020-dbt-bruin-primary-transform-engines.md) | Движки dbt (primary) + Bruin (co-primary); SQLMesh → сравнение | уточняет ADR-0004/D5; re-root #40 | Accepted |
| [0021](ADR-0021-orchestrator-transform-dq-boundary.md) | Граница ответственности оркестратор/трансформации (без дублирования DQ в Dagster) | DQ живёт в spec→dbt; оркестратор только показывает; перенумерован с 0017 | Accepted |

Новые ADR нумеруются последовательно (`ADR-NNNN-kebab-title.md`) и добавляются в эту таблицу.
