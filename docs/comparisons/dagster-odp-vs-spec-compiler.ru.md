<!-- ru-translation-of: docs/comparisons/dagster-odp-vs-spec-compiler.md sha:613d51daeefa -->
<!-- Автоперевод. Источник — docs/comparisons/dagster-odp-vs-spec-compiler.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [dagster-odp-vs-spec-compiler.md](dagster-odp-vs-spec-compiler.md)

# dagster-odp vs spec→компилятор OGIP (config-driven Dagster)

**Заданный вопрос:** можно ли использовать [dagster-odp](https://github.com/jonathanbhaskar/dagster-odp)
для этого проекта? **Вердикт: держать как референс/сравнение, не принимать на продакшен-путь** —
он пересекается с нашим существующим компилятором spec-как-SSoT и специфичен для Dagster.

## Что такое dagster-odp

Конфиго-управляемый фреймворк (PyPI `dagster-odp` 0.1.4), собирающий Dagster-пайплайны из
**YAML/JSON вместо Python**. Вы объявляете ассеты с `task_type` (например `url_file_download`,
`file_to_duckdb`, shell) и `depends_on`, а он генерирует Dagster-определения. Готовые задачи
для GCP/DuckDB/shell; интеграции с dbt, dlt, Soda; расписания/партиции из конфига.

```yaml
assets:
  - asset_key: raw_data
    task_type: url_file_download
    params: { source_url: https://example.com/data.parquet, destination_file_path: ./raw.parquet }
  - asset_key: analyzed_data
    task_type: file_to_duckdb
    depends_on: [raw_data]
```

## Почему он не подходит продакшен-пути OGIP

| Измерение | dagster-odp | OGIP сегодня |
|---|---|---|
| Источник истины | собственный YAML-DSL задач | `spec/` — **Bruin-ассеты + ODCS** ([ADR-0005](../adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md)) |
| Связанность с движком | **специфичен для Dagster** | engine-agnostic — тот же spec компилируется в **dbt** (primary), **Bruin** (co-primary), SQLMesh, plain-SQL ([ADR-0020](../adr/ADR-0020-dbt-bruin-primary-transform-engines.md)) |
| Трансформации | граф готовых задач | портируемый SQL, компилируемый под каждый движок |
| Пересечение | он *и есть* компилятор spec→Dagster | у нас уже есть `src/ogip/spec_compile` (spec→dbt/Bruin/SQLMesh) |

Его принятие ввело бы **второй, конкурирующий конфиг-DSL**, нацеленный только на Dagster,
и разрушило бы тезис «один spec, много движков». OGIP уже получает выгоду config-driven-подхода —
dbt-ассеты Dagster-альт-сетапа генерируются из `spec/` через `to_dbt.py`.

## Когда он *был бы* хорош

- Чисто Dagster-команда **без требования кросс-движковости**, которой нужны YAML-пайплайны без
  машинерии spec-компилятора — там dagster-odp даёт путь с меньшими церемониями.
- Как инструмент **прототипирования** одноразовых Dagster-графов инжеста.

## Рекомендация

Только референс. Если когда-нибудь захотим его продемонстрировать — его место в `experimental/`,
с питанием из `spec/` (эмиттер `spec → dagster-odp YAML`), чтобы `spec/` оставался SSoT —
а не как параллельная поверхность авторинга.
