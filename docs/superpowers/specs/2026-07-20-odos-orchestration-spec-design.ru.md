<!-- ru-translation-of: docs/superpowers/specs/2026-07-20-odos-orchestration-spec-design.md sha:ffae73f41d06 -->
<!-- Автоперевод. Источник — docs/superpowers/specs/2026-07-20-odos-orchestration-spec-design.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [2026-07-20-odos-orchestration-spec-design.md](2026-07-20-odos-orchestration-spec-design.md)

# ODOS 0.1 — Open Data Orchestration Standard (дизайн)

- **Дата:** 2026-07-20
- **Статус:** одобрен → [ADR-0017](../../adr/ADR-0017-odos-normative-profile.md) и
  [`spec/ODOS`](../../../spec/ODOS/README.md)
- **Lane:** `orchestration`
- **Связано с:** [ADR-0005](../../adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md) (`spec/` как SSoT) ·
  [ADR-0007](../../adr/ADR-0007-prefect-orchestration.md) (Prefect, продакшен) ·
  [ADR-0015](../../adr/ADR-0015-dagster-alt-orchestration-dg-components.md) (Dagster через `dg` Components) ·
  [ADR-0016](../../adr/ADR-0016-odts-authoring-format-spec-sql.md) (ODTS, родственный формат)

## 1. Место ODOS

Таксономия стандартов владельца трёхуровневая:

| | Название | Чем владеет |
|---|---|---|
| **YADPS** | Yet Another Data **Platform** Standard | зонтичный стандарт |
| **ODTS** | Open Data **Transformation** Standard | `spec/sql` — *что* вычисляется |
| **ODOS** | Open Data **Orchestration** Standard | `spec/orchestration` — *когда, в каком порядке и как это переживает сбой* |

`spec/sql/AGENTS.md` уже проводит эту границу с другой стороны: *«не рассматривайте оркестраторы
как цели компиляции — Prefect и Dagster **потребляют** скомпилированные проекты, это ортогональная
ось»*. ODOS и есть эта ось. Он никогда не описывает трансформацию; он ставит её в расписание.

> **Определяющее решение по именованию.** ADR-0016 называет зонтичный стандарт **YADPS**, потому что
> `ODPS` конфликтует; ODTS и ODOS сохраняют свои имена с `Open`. Этот документ следует принятой
> таксономии.

## 2. Проблема

Оркестрация в OGIP сейчас определена **дважды**, на двух несвязанных диалектах:

- `experimental/orchestration/dagster_ogip/jobs/dg-tasks.sh` — bash-диспетчер из 9 задач, привязанный
  к Dagster ops/jobs/schedules/sensors в `defs/orchestration/<group>.py` (структура уплощена
  PR #34; `warehouse/` — подпакет, разбитый на jobs/schedules/sensors);
- `pipelines/flows/_common.py` + `pipelines/flows/engines/*.py` — Python-функции шагов, обёрнутые
  в Prefect-flow и ассеты.

**Они уже разошлись.** Один и тот же логический шаг — «убедиться, что raw-данные существуют» — это:

```bash
# dg-tasks.sh:43 — Dagster lane
ensure_raw() {
  if ! ls "$REPO"/.run/data/raw/rawg__games/*.parquet >/dev/null 2>&1; then
    uv run dg launch --assets 'key:"raw/rawg__games"'      # via the orchestrator
  fi
}
```
```python
# pipelines/flows/_common.py:39 — Prefect lane
def ingest_raw() -> str:
    return RawgGames(settings).run(settings.platform.data_dir)   # straight to dlt
```

Условно против безусловно; через оркестратор против в обход него. Ничто этого не обнаруживает. Это
аналог на уровне оркестрации ODTS-угрозы `sk = md5(id)`: валидно, запускается, молча отличается.

ODOS существует, чтобы сделать такое состояние непредставимым.

## 3. Не-цели

ODOS — **внутренний для OGIP**, оценивается по переносимости между **двумя** целями (Dagster 1.13.x,
Prefect ≥3.4), а не по воображаемой индустрии. Конкретно, нельзя:

- описывать трансформации — это ODTS;
- добавлять третий оркестратор в набор целей до того, как он реально принят;
- моделировать конфигурацию инстанса/деплоя (`dagster.yaml`, storage, run coordinator) — это
  `config/config.yml` согласно жёсткому правилу 3, и дублирование создало бы второй SSoT;
- открывать множество ключей (см. §4.9);
- версионировать блоки независимо — одна версия ODOS на файл, целиком (то же правило, что у ODTS).

## 4. Формат

### 4.1 Структура

```
spec/orchestration/
  _defaults.yml       # shared partitions, owner, retry/concurrency defaults, registry root
  ingestion.yml       warehouse.yml      snapshots.yml
  maintenance.yml     integrations.yml   monitoring.yml
  _ext/dagster/       # irreducibles: dg Components (defs.yaml)
```

Один файл на **группу**. Группы соответствуют существующему разбиению
`defs/orchestration/<group>.py` (уплощённому PR #34), поэтому дифф между спецификацией и
реальностью остаётся читаемым во время миграции.

### 4.2 Скелет файла

```yaml
odos: 0.1
group: warehouse
doc: Building the DWH from raw to the FS layer.

assets:       {}    # orchestrator-native assets only (§4.4)
jobs:         {}    # units of execution (§4.3)
automations:  {}    # what starts a job (§4.5)
checks:       {}    # asset-level correctness gates (§4.6)
hooks:        {}    # location-scoped reactions (§4.6a) — rarely portable
```

Каждая секция опциональна. `odos` и `group` обязательны.

Три ключа принимаются на любом объекте в любой секции: `doc:` (свободный текст, рендерится в
`description` цели), `tags:` (словарь строк, прокидываемый в механизмы тегов обеих целей) и
`targets:` (список, ограничивающий, в какие оркестраторы компилируется объект — см. §7).

### 4.3 Джобы

Две формы, и только две:

```yaml
jobs:
  fs_job:              { select: fs.market_features }          # asset job
  dwh_assets_job:      { select: raw.rawg__games+ }            # + = downstream closure
  dwh_incremental_job: { task: dbt.build }                     # task job
  dwh_full_refresh_job:
    task: dbt.build
    args: { full_refresh: true }
    tags: { pipeline: dwh, mode: full-refresh }
```

**Грамматика `select:`** — намеренно малое подмножество, общее с конвенцией dbt/Dagster:
`name` · `name+` (замыкание вниз по графу) · `+name` (замыкание вверх по графу) · `tag:<t>` ·
список из перечисленного. Ничего больше. Никакой произвольной алгебры выборки, пока она не
понадобится второй модели.

`partitioned: true` помечает джобу, выполняющую одну партицию за запуск; это валидно, только когда
каждый выбранный ассет разделяет одно определение `partitions:`, и компилятор это проверяет.

**`select:` разрешим только потому, что ODTS публикует lineage.** Компилятор разворачивает выборку
по графу ассетов, выведенному из ODTS `depends` + `dialect.table_refs()`, плюс ассеты, объявленные
в §4.4. Это конкретная причина, по которой YADPS — одна семья, а не два несвязанных формата:
Dagster разрешает выборки нативно, у Prefect движка выборок нет вовсе, и адаптер Prefect способен
выпустить упорядоченный flow только потому, что граф уже известен статически.

### 4.4 Ассеты

Объявляются **только** для ассетов, которых нет ни в ODTS, ни в компоненте — сегодня ровно один:

```yaml
assets:
  fs.market_snapshot:
    task: snapshot.write
    partitions: daily_market        # named in _defaults.yml
    kinds: [duckdb, parquet]
    group_name: marts
```

Ассет, который оркестратор предоставляет вне ODTS и ODOS (например, нативный ассет CDC-лендинга),
объявляется с `external: true` вместо `task:` — он входит в граф для `select:`, но ни один адаптер
его не генерирует (решение 1 плана-2).

Ключи ассетов — точечные имена ODTS (`core.game`), никогда не нативные для оркестратора кортежи
ключей. Коллизия на стороне Dagster между dbt raw-моделью и dlt-ассетом (ADR-0015, «Consequences») —
забота адаптера и в спецификации не всплывает.

### 4.5 Автоматизации

Один ключ, `on:`, с закрытым набором из четырёх форм:

```yaml
automations:
  hourly_dwh_incremental: { on: cron("0 * * * *"),                        run: dwh_incremental_job }
  raw_landed_runs_dwh:    { on: asset_materialized(raw.rawg__games),      run: dwh_assets_job }
  new_postgres_raw_data:  { on: poll(sensors.landing_rowcount, every=60s), run: dwh_incremental_job }
  daily_market_snapshot:  { on: partition_ready(market_snapshot_job) }
```

`poll(...)` называет вызываемый объект реестра, возвращающий токен курсора или `None` — переносимое
ядро опрашивающего сенсора; обвязка сравнения курсора и skip-reason генерируется под каждую цель.
`partition_ready` не нуждается в `run:`; джоба — его аргумент.

### 4.6 Проверки

```yaml
checks:
  market_features_nonempty_and_scored:
    asset: fs.market_features
    task: checks.market_features_nonempty
    blocking: false
```

Ворота корректности на ассете. Согласуется с разделением ODTS: статистический мониторинг (свежесть,
объём, дрейф) — это наблюдаемость, и он принадлежит `dq/` и obs-lane, а не сюда.

### 4.6a Хуки

Реакции с областью действия на весь code location, а не на одну джобу:

```yaml
hooks:
  dwh_run_failure_alert:
    on: run_failed(scope=location)
    task: alerting.notify_run_failure
    targets: [dagster]
```

Намеренно маргинальная секция. Переносимый способ реагировать на сбой — `on_failure:` уровня джобы
(§4.7); `hooks:` существует только для того, у чего действительно нет per-job-эквивалента, и каждая
запись обязана нести ограничение `targets:`. Если §13.4 разрешится против неё, эта секция исчезнет
в 0.2.

### 4.7 Устойчивость

Самая переносимая часть формата — и та, которую первый черновик, скорее всего, упустит. Обе цели
поддерживают все три возможности нативно:

| | Dagster 1.13 | Prefect ≥3.4 |
|---|---|---|
| retry | `RetryPolicy(max_retries, delay, backoff)` | `@task(retries=, retry_delay_seconds=)` |
| concurrency | run queue + concurrency keys | лимиты конкурентности |
| on-failure | `@failure_hook` | `on_failure=[...]` (уже используется в `_common.py`) |

```yaml
jobs:
  dwh_incremental_job:
    task: dbt.build
    retry:       { max_attempts: 3, type: exponential, interval: PT1M }
    concurrency: { limit: 1, behavior: cancel }        # queue | cancel | fail
    on_failure:  alerting.notify_run_failure
```

Длительности — в ISO-8601 (`PT1M`) — однозначно, заимствовано у Kestra. Значения по умолчанию живут
в `_defaults.yml`, поэтому типичная джоба не несёт ни одного из этих ключей. По воротам ODTS
«выводи, прежде чем требовать»: директива, которую можно взять по умолчанию, не должна записываться
автором.

### 4.8 Значения по умолчанию

```yaml
# _defaults.yml
odos: 0.1
owner: data-eng@ogip
registry: ogip.tasks

partitions:
  daily_market: daily(start=2026-07-01)

defaults:
  retry:       { max_attempts: 2, type: constant, interval: PT30S }
  concurrency: { limit: 1, behavior: queue }
  on_failure:  alerting.notify_run_failure
```

Подмешиваются в каждую джобу каждого группового файла; ключ уровня джобы имеет приоритет. Та же
форма, что и блок `default:` у dag-factory.

### 4.9 Правило закрытого словаря

**Любой ключ, который ODOS не определяет, — ошибка компиляции.** Никакого проброса в конструктор
оркестратора.

Это самое большое расхождение с dag-factory, который потребляет всего четыре ключа задачи
(`operator`, `dependencies`, `task_group_name`, `parent_group_name`) и пересылает всё остальное
как есть оператору Airflow. С одной целью это удобно; с двумя неравными целями это машина тихих
потерь — ключ, который понимает Dagster, просто исчез бы из проекции Prefect, и ничто бы об этом
не сказало. Открытые множества ключей и переносимость несовместимы.

## 5. Реестр задач

Каждый `task:` называет запись в **закрытом реестре** обычных типизированных Python-функций в
`src/ogip/tasks/`. Имя — ключ реестра, а не путь импорта:

```python
@odos_task("dbt.build")
def dbt_build(*, full_refresh: bool = False, select: str | None = None,
              state: str | None = None) -> None: ...
```

Именованная регистрация вместо путей `module:function`, следуя паттерну dagster-odp
`@odp_task("...")` + `task_type:`, по трём причинам, важным именно для авторинга силами AI:

1. компилятор валидирует имя по реестру и **падает на опечатке** — путь импорта дал бы висячую
   ссылку, всплывающую только в рантайме;
2. агент выбирает из перечислимого словаря вместо того, чтобы выдумывать путь;
3. спецификация переживает реорганизацию модулей.

В отличие от dagster-odp — без сабкласса `BaseTask`: декорированной функции достаточно.
Наследование ради регистрации — церемония.

**Реестр мал.** Шесть из девяти задач `dg-tasks.sh` — одна операция с разными флагами:

```
build-dwh · build-dwh-full · dbt-evaluate · update-dbt-changed  →  dbt.build(...)
update-dbt                                                       →  dbt.parse()
dbt-deps                                                         →  dbt.deps()
```

Словарь всего проекта в проекции: `dbt.build` · `dbt.parse` · `dbt.deps` · `ingest.rawg` ·
`cdc.catchup` · `snapshot.write` · `integrations.trigger_prefect` — плюс вызываемые объекты
сенсоров и проверок. Различия переезжают в `args:`, где они видимы обеим целям.

**Регенерация неявная.** Каждая задача `dbt.*` перед действием регенерирует dbt-проект из `spec/`
(`compile_to_dbt`) и идемпотентно разрешает пакеты — ровно то, что сегодня делают `compile_dbt` и
`ensure_deps` в bash. Поскольку `spec/` — SSoT (ADR-0005), а сгенерированный проект никогда не
правится руками, спецификация, которой пришлось бы *просить* регенерацию, записывала бы факт,
который система и так знает. По правилу ODTS «выводи, прежде чем требовать»: не директива.

### 5.1 Почему нет лазейки `sh(...)`

Переходная форма `run: sh(build-dwh)` позволила бы Dagster-lane продолжать уходить в bash, пока
Prefect выполняет Python. Формат тогда не гарантировал бы ничего: одна спецификация, два поведения,
расхождение, обнаруживаемое в продакшене, а не в компиляторе. §2 показывает, что это не гипотеза —
это состояние репозитория сегодня.

**Честная цена.** Только у одной из девяти bash-задач сегодня есть полный Python-эквивалент
(`compile_dbt`, который уже heredoc-ом уходит в `ogip.spec_compile.to_dbt.compile_to_dbt`); две —
частичные (`transform/engines.py:_run_dbt`, с другим разрешением зависимостей —
`uv run --group engines` против venv проекта, и без `--full-refresh`); у четырёх задач
dbt-обслуживания эквивалента нет. Это написание трёх-четырёх тонких `subprocess`-обёрток плюс одно
настоящее решение: какая семантика `ensure_raw` — условная или безусловная — корректна. День,
а не час.

Обоснование по правилу 2 AGENTS.md («нет абстракции без двух точек вызова»): два оркестратора —
это две точки вызова.

## 6. Модель: `experimental/orchestration/dagster_ogip` в ODOS

Весь code location, шесть групп. Это заодно и приёмочный тест формата — всё, что здесь невыразимо, —
пробел формата, а не проекта.

### `warehouse.yml`

```yaml
odos: 0.1
group: warehouse
doc: Building the DWH from raw to the FS layer.

jobs:
  raw_ingest_job:      { select: raw.rawg__games,  doc: "Layer 0 — RAWG → raw Parquet via dlt." }
  staging_job:         { select: staging.stg_games }
  core_job:            { select: core.game }
  fs_job:              { select: fs.market_features }
  dwh_assets_job:      { select: raw.rawg__games+, doc: "Whole DWH: raw→stg→core→fs." }
  dwh_incremental_job: { task: dbt.build, tags: { pipeline: dwh, mode: incremental } }
  dwh_full_refresh_job:
    task: dbt.build
    args: { full_refresh: true }
    tags: { pipeline: dwh, mode: full-refresh }

automations:
  daily_dwh_full_refresh: { on: cron("0 3 * * *"),  run: dwh_full_refresh_job }
  hourly_dwh_incremental: { on: cron("0 * * * *"),  run: dwh_incremental_job }
  daily_raw_ingest:       { on: cron("30 1 * * *"), run: raw_ingest_job }
  raw_landed_runs_dwh:    { on: asset_materialized(raw.rawg__games), run: dwh_assets_job }
  new_postgres_raw_data:
    on:  poll(sensors.landing_rowcount, every=60s)
    run: dwh_incremental_job

checks:
  market_features_nonempty_and_scored:
    asset: fs.market_features
    task: checks.market_features_nonempty
    blocking: false
```

### `ingestion.yml`

```yaml
odos: 0.1
group: ingestion
assets:
  cdc.landing:
    external: true
jobs:
  dlt_ingest_job: { select: raw.rawg__games }
  cdc_asset_job:  { select: cdc.landing }
  cdc_job:        { task: cdc.catchup, args: { dry_run: true }, tags: { ingestion: cdc } }
  parsing_job:    { task: ingest.parse_to_landing, tags: { ingestion: scraping } }
automations:
  quarter_hourly_cdc: { on: cron("*/15 * * * *"), run: cdc_job }
```

### `snapshots.yml`

```yaml
odos: 0.1
group: snapshots
assets:
  fs.market_snapshot:
    task: snapshot.write
    partitions: daily_market
    kinds: [duckdb, parquet]
    group_name: marts
jobs:
  market_snapshot_job: { select: fs.market_snapshot, partitioned: true }
automations:
  daily_market_snapshot: { on: partition_ready(market_snapshot_job) }
```

### `maintenance.yml`

```yaml
odos: 0.1
group: maintenance
jobs:
  update_dbt_job:            { task: dbt.parse, tags: { maintenance: dbt } }
  update_dbt_changed_job:
    task: dbt.build
    args: { select: "state:modified+", state: "." }
    tags: { maintenance: dbt }
  dbt_project_evaluator_job:
    task: dbt.build
    args: { select: "package:dbt_project_evaluator" }
    tags: { maintenance: dbt, package: dbt_project_evaluator }
automations:
  daily_dbt_subproject_update:  { on: cron("0 2 * * *"), run: update_dbt_job }
  weekly_dbt_project_evaluator: { on: cron("0 4 * * 1"), run: dbt_project_evaluator_job }
  spec_change_updates_dbt:
    on:  poll(sensors.spec_sql_mtime, every=30s)
    run: update_dbt_changed_job
```

`state: "."` разрешается относительно `project_dir` данной lane внутри `dbt.build` — специфичный
для lane путь никогда не появляется в спецификации (решение 4 плана-2).

### `integrations.yml`

```yaml
odos: 0.1
group: integrations
jobs:
  prefect_trigger_job:
    task: integrations.trigger_prefect
    tags: { orchestration: prefect }
    targets: [dagster]        # Prefect triggering itself is meaningless
```

### `monitoring.yml`

```yaml
odos: 0.1
group: monitoring
hooks:
  dwh_run_failure_alert:
    on: run_failed(scope=location)
    task: alerting.notify_run_failure
    targets: [dagster]        # no location-scoped equivalent in Prefect
```

`monitoring.yml` — единственная группа, которой ODOS **не** владеет полностью. Переносимая форма —
`on_failure:` уровня джобы (§4.7), заданный по умолчанию в `_defaults.yml`; Dagster-сенсор с
областью действия на весь code location остаётся явно ограниченным по `targets:` дополнением,
а не фикцией переносимости.

### Компоненты

`dg` Components (`dagster_dbt.DbtProjectComponent`, `dagster_dlt.DltLoadCollectionComponent`)
остаются в `_ext/dagster/` как есть. У них вообще нет аналога в Prefect, и их абстрагирование было
бы ровно той утечкой вендора, которую запрещает ODTS. Спецификация **ссылается** на ассеты, которые
они производят; она их не описывает.

## 7. Матрица возможностей и политика отказов

| Конструкция ODOS | Dagster 1.13 | Prefect ≥3.4 | Проекция |
|---|---|---|---|
| джоба `select:` | `define_asset_job(selection=)` | нет | упорядоченный flow, выведенный из графа ODTS |
| джоба `task:` | `@job` поверх `@op` | `@flow` поверх `@task` | напрямую |
| `assets:` | `@asset` | `@materialize` | напрямую |
| `on: cron` | `ScheduleDefinition` | расписание деплоймента | напрямую |
| `on: asset_materialized` | `@asset_sensor` | Automation + `EventTrigger` (Reactive) | напрямую — §7.1 |
| `on: poll` | `@sensor` + курсор | нет (нет демона сенсоров) | деплоймент по расписанию + внешний курсор — §7.2 |
| `on: partition_ready` | `build_schedule_from_partitioned_job` | нет | cron + аргумент партиции |
| `checks:` | `@asset_check` | нет | задача-ворота валидации после ассета |
| `hooks: run_failed` | `@run_failure_sensor` | нет | ограничено по `targets:` |
| `retry`/`concurrency`/`on_failure` | нативно | нативно | напрямую |

**Политика: компилятор падает громко.** Объект, который нельзя спроецировать в запрошенную цель, —
ошибка компиляции, если он не несёт явного ограничения `targets:`. Тихо отбрасывать его запрещено —
именно так спецификация начинает лгать о том, что выполняется.

### 7.1 Проверено: Prefect выражает `asset_materialized` нативно

Установлено **запуском** Prefect 3.7.8 (установлен в `.run/venv`), а не чтением документации:

- `@materialize` эмитит `prefect.asset.materialization.succeeded` / `.failed` с
  `prefect.resource.id`, равным ключу ассета, плюс `prefect.asset.referenced` для каждого
  вышестоящего ассета. Наблюдалось для двухшагового `@materialize`-flow.
- `EventTrigger(expect={"prefect.asset.materialization.succeeded"}, match={"prefect.resource.id":
  <key>}, posture=Reactive)` + действие `RunDeployment` валидируется как `AutomationCore`.
- `Posture.Proactive` с `within=` даёт триггеры отсутствия/свежести; `MetricTrigger` тоже
  существует. Оба — OSS, без требования Cloud; эфемерный API-сервер стартует по требованию.

Так что `on: asset_materialized` — **прямая проекция на обеих целях**: это не пробел, и раннее
предположение, что он мог бы им быть, оказалось неверным. Две оговорки, найденные в том же проходе,
обе из `prefect/context.py:emit_events`: состояние `Cached` не эмитит ничего, а задача без
нижестоящего ассета не эмитит событие материализации. Любая ODOS-автоматизация, чья вышестоящая
джоба может кэшироваться, должна оговаривать это явно — иначе это будет выглядеть как пропущенный
триггер.

### 7.2 `on: poll` — единственная настоящая асимметрия

У Prefect нет держащего курсор демона сенсоров. Проекция — деплоймент по расписанию, запускающий
вызываемый объект реестра каждые `every=` и сравнивающий с курсором, хранимым вне flow. Dagster
хранит курсор за вас; Prefect — нет, поэтому **хранилище курсора — решение ODOS, а не деталь
адаптера** — иначе две проекции разойдутся ровно как в §2. Prefect Variables — очевидный кандидат;
это решение — часть задачи реализации.

### 7.3 Маппинг ключей ассетов принадлежит ODOS, а не автору flow

Ключи ассетов Prefect — URI; у Dagster — кортежи ключей. Сегодня `make_engine_flow` строит
Prefect-URI **с неймспейсом по движку** — `file://ogip/{engine}/raw/rawg__games` — так что один
логический ассет имеет разный Prefect-ключ на каждый профиль запуска. `EventTrigger` матчится по
конкретному URI, поэтому наивный порт породил бы автоматизации, срабатывающие для одного профиля
и молча никогда — для другого.

Поэтому ODOS владеет конвенцией маппинга «точечное имя → URI/кортеж ключей», и неймспейс движка
становится частью этого маппинга, а не выбором форматирования внутри модуля flow.

## 8. Архитектура компилятора

Фронтенд парсит ODOS YAML в типизированный IR (Pydantic v2, согласно жёсткому правилу 4),
разрешает `_defaults`, разворачивает `select:` по графу ассетов, выведенному из ODTS, и валидирует
каждое имя `task:`/`poll:` по реестру. Адаптеры рендерят IR:

```
spec/orchestration/*.yml ──▶ ODOS IR ──┬──▶ to_dagster.py ──▶ defs/orchestration/<group>.py
                                       └──▶ to_prefect.py ──▶ pipelines/flows/<group>.py
             ▲
    spec/sql (ODTS) ── asset graph
```

Живёт рядом со своим собратом как `src/ogip/spec_compile/` → `to_dagster.py`, `to_prefect.py`.
Ворота расширяют существующие: `just spec-compile all`, `just spec-verify`, `make check`.

**Где работает AI** (гибридная граница): компилятор детерминированно рендерит всю структуру —
джобы, выборки, расписания, каркас сенсоров, партиции, обвязку retry/concurrency, сборку
`Definitions`. Агент авторит (а) ODOS YAML и (б) тела функций реестра задач — и то и другое
обычные ревьюируемые артефакты. Между спецификацией и работающим кодом нет шага генерации.

## 9. Тестирование

- **Round-trip:** каждый групповой файл компилируется в обе цели; `spec-verify` проверяет, что
  закоммиченный вывод совпадает со свежей компиляцией.
- **Загрузка:** `dg check defs` для Dagster; импорт-и-инспекция для Prefect-flow.
- **Эквивалентность** — тест, который оправдывает формат: для джобы, присутствующей в обеих
  проекциях, проверить одну и ту же упорядоченную последовательность имён задач реестра с теми же
  args. Именно это поймало бы дрейф `ensure_raw` из §2, и это ODOS-аналог тестов конформности
  макросов ODTS.
- **Негативные:** неизвестный ключ, неизвестное имя `task:` и непроецируемый объект без
  `targets:` — каждый валит компиляцию.

## 10. Версионирование

Одна версия `odos:` на файл, целиком, зеркально ODTS. `0.1` — объём, описанный здесь. Отложено, но
явно не отвергнуто: графы задач внутри джобы (только если джобе когда-нибудь понадобится больше
одной задачи), `inputs:`/параметризованные запуски, декларации политики бэкфилла.

## 11. Отвергнутые альтернативы

- **Task-graph-first (Kestra / буквальный dag-factory)** — `jobs.tasks[].dependencies[]` с ассетами
  на вторых ролях. Естественно для Prefect, неверно для Dagster: реальный проект — это
  `define_asset_job(selection=...)` повсюду, так что формат заставил бы авторов расписывать граф,
  который Dagster выводит сам, а обратная проекция в выборки была бы с потерями. Он описывал бы
  нечто иное, чем то, что существует.
- **Только намерение + полная AI-проекция** — спецификация формулирует намерение, агент генерирует
  обе цели, golden-тесты проверяют. Максимум гибкости, но дорого по токенам и невоспроизводимо;
  отвергнуто против явного «максимизируй детерминированную поверхность» из брифа.
- **Открытый проброс ключей (dag-factory)** — см. §4.9.
- **Моделирование конфигурации инстанса/деплоя** — см. §3.

## 12. Последствия

- Оркестрация получает единый источник истины; дрейф из §2 становится падением теста.
- `dg-tasks.sh` и `pipelines/flows/_common.py` схлопываются в `src/ogip/tasks/` — реестр
  становится типизированным, pyright-strict и юнит-тестируемым, чем bash никогда не был.
- К `to_sqlmesh.py`/`to_dbt.py` присоединяется третий потребитель SSoT; ODTS и ODOS должны идти
  в ногу, и интерфейс графа ассетов между ними становится несущим.
- Цена, честно: три-четыре `subprocess`-обёртки, решение о семантике `ensure_raw`, IR + два
  адаптера и харнес тестов эквивалентности.

## 13. Открытые вопросы

1. ~~**Поверхность событий/автоматизаций Prefect ≥3.4**~~ — **разрешено запуском 3.7.8**,
   см. §7.1–7.3. `asset_materialized` проецируется напрямую; `poll` — нет и требует решения о
   хранилище курсора; маппинг ключей ассетов, как выяснилось, принадлежит ODOS. Его заменяют два
   новых подвопроса: какое хранилище курсора (Prefect Variables?) и как неймспейс движка входит
   в маппинг ключей.
2. **Семантика `ensure_raw`** — условная (пропуск при наличии parquet) или безусловная? Реестр
   должен выбрать одну, и это изменение поведения для той lane, которая проиграет.
3. **Плоские `automations:` против вложения триггеров под джобы** (`jobs[].triggers[]` у
   dagster-odp). Плоская форма держит `raw_landed_runs_dwh` привязанным к ассету, за которым он
   реально наблюдает; вложение ставит расписание рядом с тем, что оно запускает. Сейчас плоско;
   действительно спорно.
4. **Группа `monitoring`** — выживет ли она вообще после того, как `on_failure:` станет значением
   по умолчанию, или сведётся к одному Dagster-only дополнению.
