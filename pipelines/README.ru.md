<!-- ru-translation-of: pipelines/README.md sha:8a7c59905856 -->
<!-- Автоперевод. Источник — pipelines/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# `pipelines/`

Flow и деплойменты **Prefect 3** (ADR-0007). Разделённые, независимо деплоящиеся через
`prefect deploy` подпроекты используют ОДНУ библиотеку шагов — без дублирования на движок.
**Основные** подпроекты (dbt · bruin, [ADR-0020](../docs/adr/ADR-0020-dbt-bruin-primary-transform-engines.md))
живут здесь; пять сравнительных подпроектов (`sqlmesh`, `plain_sql`, `opendbt`,
`sqlmesh_dbt`, `dagster`) живут в [`experimental/pipelines/`](../experimental/pipelines/)
(re-root #40) с той же формой.

| Подкаталог | Содержит |
|---|---|
| `_shared/` | Единственная библиотека шагов: `steps.py` (`ingest_raw`, `build_warehouse`, `build_ml_outputs`, `publish_outputs`, `make_engine_flow`), `alerting.py` (`notify_flow_failure`), `paths.py` (константы путей относительно репозитория), `engines.py` (`ENGINE_FLOWS`: имя transform → модуль подпроекта, основного или экспериментального) |
| `dbt/`, `bruin/` | Два основных Prefect-подпроекта (матрица run-профилей A12). Каждый — `{__init__.py, flow.py, prefect.yaml}`: `flow.py` импортирует `pipelines._shared.steps` и экспонирует ровно один объект `flow`; `prefect.yaml` — собственное определение деплоймента этого подпроекта, деплоится сам по себе (`prefect deploy` изнутри каталога), не затягивая остальные |
| `flows/` | Только `main.py` — каноническая точка входа. Реэкспортирует **основной** сетап (`pipelines.dbt.flow`) как `ingest_transform_publish`, поэтому `make run`, e2e-тест и `src/ogip/tasks/integrations.py` (который вызывает `python -m pipelines.flows.main` через shell) продолжают работать без изменений |

## Как run-профиль разрешается во flow

`src/scripts/run-profile.py` читает `config/config.yml → run_profiles[<name>].transform`, ищет
его в `pipelines._shared.engines.ENGINE_FLOWS` и импортирует `flow` этого подпроекта — ничто не
импортирует все семь жадно (зависимости подпроекта `dagster` тяжелее и остаются опциональными,
пока этот профиль реально не выбран). Экспериментальные профили печатают баннер `[EXPERIMENTAL]`.

## Подпроект Dagster: Prefect — ВНЕШНИЙ оркестратор

`experimental/pipelines/dagster/flow.py` — единственный подпроект, который не является простым
SQL-runner'ом: Prefect остаётся внешним оркестратором платформы, но связка **dlt-инжест +
dbt-transform** выполняется *под* Dagster (`experimental/orchestration/dagster_ogip`, через
`dg launch`) — Dagster владеет той узкой, имеющей форму asset-графа частью, в которой он лучше
всех. Prefect оборачивает этот шаг в asset `@materialize`, затем сам выполняет ML-матрицу фичей
и публикацию, как и с любым другим движком. Это шов между двумя оркестраторами над одним общим
хранилищем.

_Строится начиная с фазы 6; M0 подключил минимальный end-to-end flow; части 3.1–3.3 (#37)
извлекли общую библиотеку шагов и разделили каждый движок в собственный деплоящийся подпроект._
