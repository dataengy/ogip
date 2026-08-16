<!-- ru-translation-of: spec/ODOS/IMPLEMENTATION.md sha:94034d07df55 -->
<!-- Автоперевод. Источник — spec/ODOS/IMPLEMENTATION.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [IMPLEMENTATION.md](IMPLEMENTATION.md)

# ODOS 0.1 — описание реализации в OGIP

[`examples/`](examples/README.md) — нормативная шестигрупповая модель соответствия. Этот документ
привязывает каждый объект из этих фикстур к коду, который реализует его сегодня:
[`experimental/orchestration/dagster_ogip/`](../../experimental/orchestration/dagster_ogip/README.md)
(проекция Dagster) и [`pipelines/_shared/`](../../pipelines/_shared/) + семь
по-движковых подпроектов в `pipelines/<engine>/` (проекция Prefect) — оба на данный момент
написаны вручную. Компилятор ODOS
([#37](https://github.com/dataengy/ogip/issues/37)) будет генерировать обе стороны из строчного
`spec/orchestration/`; до тех пор это соответствие — чек-лист ревью для вопроса *«всё ли ещё
фикстуры описывают реальность?»*.

## Статус одним взглядом

| Слой ODOS | Состояние |
|---|---|
| Реестр задач (`registry: ogip.tasks`) | **работает** — [`src/ogip/tasks/`](../../src/ogip/tasks/), десять записей `@odos_task` |
| Проекция Dagster | написана вручную — `defs/orchestration/<group>/definitions.py`, шесть групп |
| Проекция Prefect | написана вручную — `make_engine_flow` в [`pipelines/_shared/steps.py`](../../pipelines/_shared/steps.py), обёрнутый **семью** раздельными, независимо развёртываемыми подпроектами: два основных в `pipelines/{dbt,bruin}/` + пять сравнительных в `experimental/pipelines/{sqlmesh,plain_sql,opendbt,sqlmesh_dbt,dagster}/` (ADR-0020, re-root #40), у каждого свой `prefect.yaml` |
| Дрейф §2 проектного документа (`ensure_raw`) | **устранён на уровне задач** — обе lane вызывают одни и те же функции реестра |
| Компилятор, адаптеры, тест эквивалентности | не построены — оставшийся объём работ по [#37](https://github.com/dataengy/ogip/issues/37) |

## 1. Реестр задач

`_defaults.yml` объявляет `registry: ogip.tasks`. Каждое имя ниже разрешается в обычную
типизированную функцию в [`src/ogip/tasks/`](../../src/ogip/tasks/), зарегистрированную через
`@odos_task("<name>")` ([`_registry.py`](../../src/ogip/tasks/_registry.py)) и вызываемую из
CLI как `python -m ogip.tasks <name> --flag=value`.

| Имя в реестре | Модуль | Потребители |
|---|---|---|
| `dbt.build` | `tasks/dbt.py` | Dagster `build-dwh`, `build-dwh-full`, `dbt-evaluate`, `update-dbt-changed`; Prefect `build_warehouse("dbt")` |
| `dbt.parse` | `tasks/dbt.py` | Dagster `update-dbt` |
| `dbt.deps` | `tasks/dbt.py` | Dagster `dbt-deps` |
| `ingest.rawg` · `ingest.metacritic` · `ingest.all` | `tasks/ingest.py` | Шаг `_ingest` в Prefect (`ingest_raw = ingest_all`) |
| `ingest.parse_to_landing` | `tasks/ingest.py` | Dagster `parsing` |
| `cdc.catchup` | `tasks/cdc.py` | Dagster `cdc [--dry-run\|--stream]` |
| `integrations.trigger_prefect` | `tasks/integrations.py` | Dagster `prefect` |
| `snapshot.write` | `tasks/snapshots.py` | сегодня только CLI — см. §3, снапшоты |

Сторона Dagster обращается к реестру через
[`jobs/dg-tasks.sh`](../../experimental/orchestration/dagster_ogip/jobs/dg-tasks.sh), девять
задач которого теперь — **тонкие алиасы** (`ogip_task() { … python -m ogip.tasks "$@"; }`);
сторона Prefect импортирует те же функции напрямую. Именно это растворило дрейф §2
руководящего проектного документа: «ensure raw» больше не существует как задача ни на одной из
сторон — граф активов Dagster выражает `raw → dbt`, а поток Prefect выполняет `ingest.all`
явным первым шагом.

Имена, на которые ссылаются фикстуры, но которые **ещё не являются записями реестра** (тела
по-прежнему живут инлайн):

| Имя в фикстуре | Где сегодня живёт тело |
|---|---|
| `checks.market_features_nonempty` | `market_features_check` в `defs/orchestration/warehouse/definitions.py` |
| `sensors.landing_rowcount` | `new_postgres_raw_sensor` в `defs/orchestration/warehouse/definitions.py` |
| `sensors.spec_sql_mtime` | `spec_change_sensor` в `defs/orchestration/maintenance/definitions.py` |
| `alerting.notify_run_failure` | Prefect: [`pipelines/_shared/alerting.py`](../../pipelines/_shared/alerting.py) `notify_flow_failure`; Dagster: `dwh_failure_sensor` (только логирование) |

Извлечение этих четырёх имён в реестр — подготовка к компилятору: `poll(...)` и `checks:`
можно валидировать только по существующим именам.

## 2. Соответствие по группам

Каждый объект Dagster ниже живёт в
`experimental/orchestration/dagster_ogip/src/dagster_ogip/defs/orchestration/<group>/definitions.py`.

### `warehouse.yml`

| Объект фикстуры | Реализация в Dagster |
|---|---|
| джоб `raw_ingest_job` — `select: raw.rawg__games` | `define_asset_job` поверх актива dlt-компонента (`K_RAW_DLT`) |
| джобы `staging_job` · `core_job` · `fs_job` | `define_asset_job` поверх активов dbt-компонента (`K_STAGING` · `K_CORE` · `K_FS`) |
| джоб `dwh_assets_job` — `select: raw.rawg__games+` | `AssetSelection.assets("rawg__games").downstream()` |
| джоб `dwh_incremental_job` — `task: dbt.build` | `@dg.job` → `dg-tasks.sh build-dwh` |
| джоб `dwh_full_refresh_job` — `task: dbt.build, args: {full_refresh: true}` | `@dg.job` → `dg-tasks.sh build-dwh-full` |
| автоматизации `daily_dwh_full_refresh` · `hourly_dwh_incremental` · `daily_raw_ingest` | три `ScheduleDefinition` с теми же cron-строками |
| автоматизация `raw_landed_runs_dwh` — `asset_materialized(raw.rawg__games)` | `@dg.asset_sensor` `raw_landed_sensor` |
| автоматизация `new_postgres_raw_data` — `poll(sensors.landing_rowcount, every=60s)` | `@dg.sensor` `new_postgres_raw_sensor`, `minimum_interval_seconds=60`, число строк в роли курсора |
| проверка `market_features_nonempty_and_scored` — `blocking: false` | `@dg.asset_check(blocking=False)` `market_features_check` |

### `ingestion.yml`

| Объект фикстуры | Реализация в Dagster |
|---|---|
| джоб `dlt_ingest_job` — `select: raw.rawg__games` | `define_asset_job` поверх `K_RAW_DLT` |
| джоб `cdc_asset_job` — `select: cdc.landing` | `define_asset_job` поверх `K_CDC` (`defs/cdc_ingest/`) |
| джоб `cdc_job` — `task: cdc.catchup, args: {dry_run: true}` | `@dg.job` → `dg-tasks.sh cdc --dry-run` |
| джоб `parsing_job` — `task: ingest.parse_to_landing` | `@dg.job` → `dg-tasks.sh parsing` |
| джоб `metacritic_ingest_job` — `task: ingest.metacritic` | задача реестра работает (`src/ogip/tasks/ingest.py`); джоб Dagster ещё не подключён — Prefect достигает её через `ingest.all` при `sources.metacritic.enabled` |
| автоматизация `quarter_hourly_cdc` — `cron("*/15 * * * *")` | `ScheduleDefinition quarter_hourly_cdc` |

### `snapshots.yml`

| Объект фикстуры | Реализация в Dagster |
|---|---|
| актив `fs.market_snapshot` — `task: snapshot.write, partitions: daily_market` | `@dg.asset market_snapshot`, `DailyPartitionsDefinition(start_date="2026-07-01")` = `daily(start=2026-07-01)` |
| джоб `market_snapshot_job` — `partitioned: true` | `define_asset_job(..., partitions_def=snapshot_partitions)` |
| автоматизация `daily_market_snapshot` — `partition_ready(market_snapshot_job)` | `build_schedule_from_partitioned_job` |

**Известное остаточное дублирование:** тело актива `market_snapshot` инлайнит SQL снапшота
вместо вызова реестрового `snapshot.write` — один и тот же оператор COPY существует дважды.
Фикстура фиксирует целевое состояние (`task: snapshot.write`); тело актива — тот дрейф,
который устраняет компилятор.

### `maintenance.yml`

| Объект фикстуры | Реализация в Dagster |
|---|---|
| джоб `update_dbt_job` — `task: dbt.parse` | `@dg.job` → `dg-tasks.sh update-dbt` |
| джоб `update_dbt_changed_job` — `args: {select: "state:modified+", state: dbt}` | `@dg.job` → `dg-tasks.sh update-dbt-changed` (`state:` = каталог сгенерированного dbt-проекта; конкретный путь — зона ответственности адаптеров) |
| джоб `dbt_project_evaluator_job` — `args: {select: "package:dbt_project_evaluator"}` | `@dg.job` → `dg-tasks.sh dbt-evaluate` |
| автоматизации `daily_dbt_subproject_update` · `weekly_dbt_project_evaluator` | две `ScheduleDefinition`, те же cron-выражения |
| автоматизация `spec_change_updates_dbt` — `poll(sensors.spec_sql_mtime, every=30s)` | `@dg.sensor spec_change_sensor`, mtime спеки в роли курсора |

### `integrations.yml`

| Объект фикстуры | Реализация в Dagster |
|---|---|
| джоб `prefect_trigger_job` — `task: integrations.trigger_prefect, targets: [dagster]` | `@dg.job` → `dg-tasks.sh prefect`. Только Dagster по построению: Prefect, запускающий сам себя, бессмыслен |

### `monitoring.yml`

| Объект фикстуры | Реализация в Dagster |
|---|---|
| хук `dwh_run_failure_alert` — `run_failed(scope=location), targets: [dagster]` | `@dg.run_failure_sensor dwh_failure_sensor` (сегодня только логирование; точка подключения — Notifier из lane алертинга) |

Портируемый путь обработки сбоев — не этот хук, а
`on_failure: alerting.notify_run_failure` из `_defaults.yml` — уже реальный на стороне
Prefect как `@flow(on_failure=[notify_flow_failure])`.

## 3. Компоненты — упоминаются, но не описываются

Согласно [SPEC.md](SPEC.md) §1, оркестраторные Components остаются вне портируемых документов.
Фикстуры *ссылаются* на активы, которые те производят (`raw.rawg__games`, `staging.stg_games`,
`core.game`, `fs.market_features`, `cdc.landing`); сами компоненты — нативные для Dagster:

| Компонент | Файл | Производит |
|---|---|---|
| `dagster_dbt.DbtProjectComponent` | `defs/dbt_ingest/defs.yaml` (`select: "tag:daily"`) | граф dbt-активов, сгенерированный из `spec/` |
| `dagster_dlt.DltLoadCollectionComponent` | `defs/dlt_ingest/defs.yaml` | `raw.rawg__games` |
| CDC-актив | `defs/cdc_ingest/definitions.py` | `cdc.landing` |

## 4. Проекция Prefect

[`make_engine_flow`](../../pipelines/_shared/steps.py) — сегодняшний рукописный эквивалент
проекции упорядоченного потока: один поток на движок, выполняющий цепочку
`ingest.all → build_warehouse(engine) → build_ml_outputs → publish_outputs` шагами
`@materialize`. В терминах фикстур это соответствует `dwh_assets_job`
(`select: raw.rawg__games+`), расширенному ML/publish-хвостом, который принадлежит
производственному конвейеру, а не шестигрупповой модели.

Начиная с части 3 [плана расширения
transform](../../docs/superpowers/plans/2026-07-23-transform-expansion-and-six-prefect-subprojects.md)
(см. [ADR-0019](../../docs/adr/ADR-0019-odts-dq-projection-and-seven-prefect-subprojects.md))
проекция больше не устроена как один общий `_common.py` плюс тонкий однострочный модуль на
движок — та компоновка (`pipelines/flows/engines/prefect_*.py` поверх
`pipelines/flows/_common.py`) была списана, как только все потребители стали разрешаться через
подпроекты. Библиотека шагов теперь живёт в одном месте —
в [`pipelines/_shared/`](../../pipelines/_shared/) (`steps.py` — `ingest_raw`, `build_warehouse`,
`build_ml_outputs`, `publish_outputs`, `make_engine_flow`; `alerting.py` —
`notify_flow_failure`; `paths.py` — константы путей относительно корня репозитория;
`engines.py` — `ENGINE_FLOWS`, отображение имени transform → модуля подпроекта), а каждый из
семи профилей SQL/оркестрации
(`sqlmesh`, `plain_sql`, `dbt`, `opendbt`, `sqlmesh_dbt`, `bruin`, `dagster`) — собственный
каталог: основные в `pipelines/<engine>/`, сравнительные конфигурации в
`experimental/pipelines/<engine>/` (ADR-0020) — `{__init__.py, flow.py, prefect.yaml}` —
развёртываемый через `prefect deploy` отдельно, не затягивая остальные.
`pipelines/flows/main.py` сохраняется лишь как реэкспорт `ingest_transform_publish` из
`pipelines.dbt.flow` (основная конфигурация), потому что `src/ogip/tasks/integrations.py`
вызывает через шелл `python -m pipelines.flows.main`, и эта точка входа должна оставаться
импортируемой по историческому пути. `src/scripts/run-profile.py` разрешает имя
`config.yml run_profiles[<name>].transform` через `ENGINE_FLOWS`, а не импортирует все семь
жадно. Подпроект `dagster` (`experimental/pipelines/dagster/flow.py`) — единственное исключение
из простой по-движковой формы: Prefect остаётся внешним оркестратором, но связка
dlt-ingest + dbt выполняется *под* Dagster (`dg launch`) — см.
[`pipelines/README.md`](../../pipelines/README.md), раздел «Dagster sub-project», и §3 ниже о
Components, которые она оборачивает.

Здесь видны два факта, которые руководящий проектный документ (§7.3) относит к ODOS:

- **Ключи активов — URI с пространством имён движка** — `file://ogip/{engine}/raw/rawg__games`,
  `duckdb://ogip/{engine}/core.game`. Поэтому один логический актив имеет разный ключ Prefect
  в каждом профиле запуска; отображение точечного имени → URI (и то, останется ли в нём
  пространство имён движка) — решение компилятора ODOS, а не выбор автора потока.
- **`on_failure` уже портируем** — `@flow(on_failure=[notify_flow_failure])` — это в точности
  `on_failure: alerting.notify_run_failure` из `_defaults.yml`, отрендеренный вручную.

## 5. Что компилятор ещё должен ([#37](https://github.com/dataengy/ogip/issues/37))

- IR + фронтенд (слияние значений по умолчанию, разворачивание `select:` по линеажу ODTS,
  валидация реестра, соблюдение закрытого словаря) и адаптеры `to_dagster.py` / `to_prefect.py`.
- **Тест эквивалентности** — одна и та же упорядоченная последовательность имён задач реестра +
  аргументов в обеих проекциях; шлюз, превращающий дрейф в падение CI вместо надежды на
  код-ревью.
- Извлечение в реестр четырёх инлайновых имён из §1, плюс дублирование `snapshot.write` в §2
  (снапшоты).
- Хранилище курсоров `poll` для Prefect (кандидат — Prefect Variables) и упомянутое выше
  решение по отображению ключей активов.
- Живые документы `spec/orchestration/*.yml`, замещающие обе рукописные проекции.
