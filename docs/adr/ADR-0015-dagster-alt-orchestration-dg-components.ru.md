<!-- ru-translation-of: docs/adr/ADR-0015-dagster-alt-orchestration-dg-components.md sha:d81cfc2723d9 -->
<!-- Автоперевод. Источник — docs/adr/ADR-0015-dagster-alt-orchestration-dg-components.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0015-dagster-alt-orchestration-dg-components.md](ADR-0015-dagster-alt-orchestration-dg-components.md)

# ADR-0015 — Альтернативная оркестрация на Dagster через `dg`-компоненты (dbt + dlt + ingestr CDC)

- **Статус:** Принято
- **Дата:** 2026-07-17
- **Связано с:** [ADR-0007](ADR-0007-prefect-orchestration.md) (Prefect + запускаемые альтернативные setup'ы),
  [ADR-0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md) (spec SSoT + компилятор), D1/D11

## Контекст

Профиль `prefect-dagster-dlt-dbt` (A12) — один из запускаемых альтернативных setup'ов, обещанных
ADR-0007: вне продакшн-пути, чтобы сравнить asset-центричный оркестратор с
дефолтным путём Prefect+SQLMesh. Ему нужна конкретная, актуальная реализация.

## Решение

Собрать его на **современном подходе Dagster — CLI `dg` + компоненты** (`create-dagster
project`, `dg scaffold defs`, `dg check defs`, `dg launch --assets`), изолированно в
самодостаточном uv-проекте под `experimental/orchestration/dagster_ogip/`, чтобы зависимости Dagster
никогда не касались продакшн-окружения.

- **dbt** через `dagster_dbt.DbtProjectComponent` (`project: "{{ project_root }}/dbt"`,
  `select: "tag:daily"`). Проект dbt **генерируется из `spec/`** через `to_dbt.py` — spec/
  остаётся SSoT: зависимости Bruin → `{{ ref() }}`, `tags` Bruin → теги dbt (управляют `tag:daily`),
  `checks` Bruin → тесты dbt, схемы слоёв через макрос `generate_schema_name`.
- **dlt** через `dagster_dlt.DltLoadCollectionComponent` — RAWG → сырой Parquet, тот же контракт
  Layer-0, что и в линии Prefect (`file_format="parquet"` закреплён на ресурсе).
- **ingestr CDC** (D11) как `@dg.asset`, вызывающий из шелла `cdc/ingestr_cdc.sh` — единственный CDC-
  конвейер, из landing-зоны Postgres.
- **dev** = SQLite в `DAGSTER_HOME`; **prod** = хранилище Postgres (только env-ссылки, ADR-0011),
  `QueuedRunCoordinator`.
- **Версия:** Dagster **1.13.x** (никакого «Dagster 4» не существует; на момент решения последней была 1.13.14).

## Последствия

- Asset-центричная оркестрация демонстрируема и **e2e-протестирована** (`e2e/run_combo.sh`, отдельный
  CI-workflow `dagster-e2e`) — source → слой FS за один прогон, включая тесты dbt как DQ.
- Два потребителя SSoT (`to_sqlmesh.py`, `to_dbt.py`) должны оставаться синхронными с изменениями `spec/`.
- Ключ ассета dbt `raw/<table>` конфликтует с ключом ассета dlt, поэтому сырая модель dbt
  оставлена без квалификации схемы (view внешней регистрации; настоящий производитель — ассет dlt).

## Рассмотренные альтернативы

- **Написанный вручную граф Dagster `@asset`** — отклонено: компоненты — это текущая идиома, и они держат
  обвязку dbt/dlt декларативной в `defs.yaml`.
- **Второй, сопровождаемый вручную dbt-проект** — отклонено: нарушает spec-as-SSoT; генерируйте его.
