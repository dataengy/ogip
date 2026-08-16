<!-- ru-translation-of: spec/ODTS/IMPLEMENTATION.md sha:fec03186b86c -->
<!-- Автоперевод. Источник — spec/ODTS/IMPLEMENTATION.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [IMPLEMENTATION.md](IMPLEMENTATION.md)

# ODTS 0.1 — реализация OGIP, описание

Этот документ описывает стек преобразований OGIP в терминах стандарта:
[`spec/sql/`](../sql/AGENTS.md) — слой авторинга,
[`src/ogip/spec_compile/`](../../src/ogip/spec_compile/) — компилятор, а
[`transform/`](../../transform/README.md) содержит шесть скомпилированных проекций. Парный
документ по оркестрации — [ODOS IMPLEMENTATION](../ODOS/IMPLEMENTATION.md).

## Статус одним взглядом

| Слой ODTS | Состояние |
|---|---|
| Документы авторинга | шестнадцать моделей в `spec/sql`, сейчас на легаси-заголовке `@bruin`; миграция на `@odts` — [#35](https://github.com/dataengy/ogip/issues/35) |
| Фронтенд (`@odts` → легаси-YAML) | запланирован — [#35](https://github.com/dataengy/ogip/issues/35) |
| Реестр макросов (`@keys.hash`, `@dates.year`) | запланирован — [#36](https://github.com/dataengy/ogip/issues/36); суррогатные ключи сегодня — рукописный `md5(...)` |
| IR + адаптеры (шесть целей) | **работает** — `parse_asset()` → `Asset` → `to_sqlmesh` · `to_dbt` · `to_bruin` · `to_sqlmesh_dbt`; plain SQL потребляет `spec/sql` напрямую |
| Lineage, переписывание ссылок, ретаргетинг | **работает** — `spec_compile/dialect.py` (sqlglot), в границах AST |
| Форматтер | **работает** — sqlfluff, единственный форматтер (`just sql-lint`) |

## 1. Слой авторинга — `spec/sql`

Шесть документов, по одному на модель, путь = `<layer>/<name>.sql`, строящие
`raw → staging → core → fs` (именование слоёв — закон проекта; никакого medallion-словаря):

| Модель | Вид | Семантический класс (теги) | Объявленные ограничения |
|---|---|---|---|
| `raw.rawg__games` | view | `raw, rawg, daily` | нет — регистрация 1:1 неизменяемого raw Parquet |
| `raw.metacritic__game` | view | `raw, metacritic, daily` | нет — регистрация 1:1 неизменяемого raw Parquet |
| `staging.stg_games` | table | `staging, rawg, daily` | `game_id` !null unique · `name` !null |
| `staging.stg_metacritic_games` | table | `staging, metacritic, daily` | `slug` !null unique · `name` !null · `metascore` non_negative |
| `core.game` | table | `core, entity, daily` | `game_sk` pk !null unique · `title` !null |
| `fs.market_features` | table | `fs, feature-store, daily` | `game_sk` !null unique · `popularity_score` non_negative |

Цепочка зависимостей — ровно такая, какой её предписывает §4 [профиля](SPEC.md): выводимая из
SQL AST, поэтому `@odts`-форма этих документов вообще не пишет `depends` — см.
[`examples/`](examples/README.md), где переоформлены заголовки именно этих четырёх моделей.

## 2. Компилятор — `src/ogip/spec_compile`

IR-конвейер из SPEC.md §9, каким он существует сегодня:

- `parse_asset()` читает заголовок в типизированный `Asset` — каноническую модель; текст
  заголовка ею не является никогда.
- `dialect.py` (sqlglot) владеет всем, что должно понимать SQL: `table_refs()` (lineage —
  граф, который потребляет разворачивание `select:` в ODOS), `rewrite_refs()`
  (`staging.stg_games` → `{{ ref('stg_games') }}` в границах AST), `transpile()` (DuckDB →
  Postgres / ClickHouse / BigQuery, прогоняется тестами при каждом запуске).
- Фронтенд `@odts` ([#35](https://github.com/dataengy/ogip/issues/35)) расширяет это
  спереди — рендеря компактный заголовок в легаси-текст YAML `@bruin`, который уже требуют
  `parse_asset()` и одна цель с дословным копированием, — и ничего позади себя не
  переписывает.

## 3. Шесть проекций — `transform/`

Каждый каталог **генерируется из `spec/`**; ни один не написан вручную.
[`transform/engines.py`](../../transform/engines.py) перегенерирует проект движка из спеки
непосредственно перед запуском, поэтому устаревший checkout не может разойтись с SSoT.

| Цель | Адаптер | Расположение | Профиль запуска | Роль |
|---|---|---|---|---|
| dbt | `to_dbt.py` | `transform/dbt/` | `prefect-dbt`, `prefect-dagster-dlt-dbt` | **основная** ([ADR-0020](../../docs/adr/ADR-0020-dbt-bruin-primary-transform-engines.md)); её же загружает `DbtProjectComponent` проектного Dagster |
| Bruin | `to_bruin.py` | `transform/bruin/` | `prefect-bruin` | **со-основная** — ассеты копируются дословно (легаси-заголовок *и есть* формат Bruin) |
| SQLMesh | `to_sqlmesh.py` | `transform/sqlmesh/` | `prefect-sqlmesh` | сравнение (продакшен-умолчание до ADR-0020) |
| OpenDBT | `to_dbt.py` | `transform/opendbt/` | `prefect-opendbt` | сравнение (расширенный dbt-core) |
| SQLMesh-over-dbt | `to_sqlmesh_dbt.py` | `transform/sqlmesh_dbt/` | `prefect-sqlmesh-over-dbt` | сравнение |
| plain SQL | нет — потребляет `spec/sql` напрямую | `transform/runner.py` | `prefect-sql` | сравнение — топологически сортирует `depends`, `create or replace` на DuckDB |

Сгенерированные проекты коммитятся (ревьюируемые diff-ы при изменении спеки) и несут пути
относительно репозитория. Колоночные `checks` становятся тестами dbt `schema.yml`, проверками
Bruin, аудитами SQLMesh — одно объявление, рендеринг под каждую цель, как требует SPEC.md §6.

### DQ-проекция: `checks:` → аудиты SQLMesh

`to_sqlmesh.py` (`_audits` / `_audit_for`) проецирует каждую запись `columns[].checks` — плюс
составную верхнеуровневую форму `checks: [{name: unique, columns: [...]}]` — в клаузу
`audits (...)` блока `MODEL(...)`. Раньше это было молчаливым отбрасыванием (`_model_text`
выдавал `MODEL(name, kind)` и полностью отбрасывал `columns.checks`); теперь компилятор
отрисовывает каждую проверку, а нераспознанное имя проверки — это `SqlSpecError` на этапе
компиляции — «атрибуты вне словаря проверок MUST приводить к ошибке компиляции» из SPEC.md
§5 — и никогда не молчаливый пропуск.

| Проверка ODTS | Аудит SQLMesh |
|---|---|
| `not_null` | `not_null(columns := (col))` |
| `unique` (на уровне колонки) | `unique_values(columns := (col))` |
| `non_negative` | `accepted_range(column := col, min_v := 0)` |
| `between(a, b)` | `accepted_range(column := col, min_v := a, max_v := b)` |
| `accepted_values(v1, ...)` | `accepted_values(column := col, is_in := (v1, ...))` |
| верхнеуровневый `unique(columns: [...])` | `unique_combination_of_columns(columns := (...))` |
| всё остальное | `SqlSpecError` на этапе компиляции — никогда не отбрасывается молча |

Сегодня так рендерятся 70 аудитов по raw/staging/core/fs (комплексный DQ-проход
[плана расширения transform](../../docs/superpowers/plans/2026-07-23-transform-expansion-and-six-prefect-subprojects.md)).

**Граница ODTS §6 — проверки ≠ мониторы.** В `columns[].checks:` принадлежат только
ограничения корректности (таблица выше). **Мониторы** свежести и числа строк — отдельная
забота, объявляемая в [`spec/dq/policy.yml`](../dq/policy.yml) — никогда не в `checks:` в
`spec/sql` — и загружаемая + репортуемая (пока не исполняемая) [`dq/run.py`](../../dq/run.py);
исполнитель (запросить хранилище, оценить пороги, записать в `platform_meta.dq_results`) — это
Фаза 4. Запись `checks:`, имеющая форму монитора (`freshness`, `row_count`), — дефект спеки, а
не альтернативный стиль авторинга.

**Известный пробел — аудиты компилируются, но не исполняются гейтом по умолчанию.** `make
check` запускает `pytest -m "not integration and not e2e"`; сгенерированные клаузы
`audits (...)` вычисляются только тогда, когда SQLMesh действительно планирует/применяет
против хранилища (`sqlmesh plan --auto-apply`), что происходит в
`src/tests/e2e/test_all_setups.py::test_base_setup_builds_and_produces_ml -k
sqlmesh` (помечен `e2e`, исключён из `make check`) или в живом запуске `prefect-sqlmesh`.
Регрессия в отрендеренном аудите `not_null`/`accepted_range` может чисто компилироваться и
проходить `make check`, оставаясь сломанной во время выполнения — ловит её только e2e-тест
(или ручной запуск `sqlmesh audit`). См.
[ADR-0019](../../docs/adr/ADR-0019-odts-dq-projection-and-seven-prefect-subprojects.md).

Граница, которую проводит семейство стандартов, видна в потребителях этой таблицы: Prefect и
Dagster в ней нигде не появляются. Оркестраторы потребляют эти скомпилированные проекты через
реестр задач ODOS (`dbt.build` перегенерирует, затем собирает; `build_warehouse("sqlmesh")`
компилирует, затем планирует) — это ось ODOS, никогда не цели ODTS.

## 4. Статус соответствия SPEC.md §9

| Требование | Статус |
|---|---|
| Перегенерация целей + идентичность закоммиченного вывода | **зелёный** — `just spec-compile all` · `just spec-verify` |
| Ретаргетинг диалекта остаётся парсируемым | **зелёный** — ретаргет-тесты гоняются по каждой модели при каждом `make check` |
| Идентичность фикстур/спеки для пакета стандарта | **зелёный** — `just standards-validate` |
| Round-trip `@odts` (отрендеренный легаси-заголовок ≡ рукописному) | ожидает [#35](https://github.com/dataengy/ogip/issues/35) |
| Утверждение `depends` падает при расхождении с AST | ожидает [#35](https://github.com/dataengy/ogip/issues/35) |
| Десахаризация LValue `:=` / отклонение `=` | ожидает [#35](https://github.com/dataengy/ogip/issues/35) |
| Соответствие макросов (побайтовая идентичность по каждому адаптеру) | ожидает [#36](https://github.com/dataengy/ogip/issues/36) |
