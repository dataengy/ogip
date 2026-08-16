<!-- ru-translation-of: transform/README.md sha:4851199b3209 -->
<!-- Автоперевод. Источник — transform/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# `transform/`

Каждый setup трансформаций здесь **генерируется из `spec/sql`** (формат ассетов Bruin, SSoT —
[ADR-0005](../docs/adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md)); ни один не написан вручную.
Перегенерировать все: `just spec-compile` (один движок: `just spec-compile dbt`).

**Продакшен — это SQLMesh на DuckDB, порядок запуска задаёт Prefect** ([ADR-0004](../docs/adr/ADR-0004-sqlmesh-default-transform-engine.md), D5).
Остальные существуют для того, чтобы `docs/comparisons/*` измерял реальные прогоны. Сборка идёт `staging → core → star / am → marts → fs`.

| Путь | Профиль (`just run-profile …`) | Что это |
|---|---|---|
| `sqlmesh/` | `prefect-sqlmesh` **(по умолчанию, продакшен)** | нативные модели SQLMesh |
| `runner.py` | `prefect-sql` | раннер чистого SQL — без фреймворка: топологическая сортировка `depends`, `create or replace` на DuckDB |
| `dbt/` | `prefect-dbt`, `prefect-dagster-dlt-dbt` | сгенерированный dbt-проект (+ пакеты dbt-hub, тесты `schema.yml` из Bruin-проверок `checks`) |
| `opendbt/` | `prefect-opendbt` | те же модели через **OpenDBT** (расширенный dbt-core: python/dlt-модели, mesh-ссылки, кастомные адаптеры) — собственная группа зависимостей, пин dbt <1.10 |
| `sqlmesh_dbt/` | `prefect-sqlmesh-over-dbt` | тот же dbt-проект + `config.py`, чтобы SQLMesh нативно планировал/применял его |
| `bruin/` | `prefect-bruin` | pass-through — `spec/` *и есть* Bruin, поэтому ассеты копируются дословно + оболочка проекта |
| `engines.py` | — | лаунчер: перегенерирует проект движка из `spec/`, затем запускает его |

Четыре снапшота движков **закоммичены** — `dbt/`, `opendbt/`, `sqlmesh_dbt/`, `bruin/`
(просматриваемые диффы при изменении спеки) — и содержат пути относительно корня репозитория,
поэтому запускайте каждый движок **из корня репозитория**. Перегенерируйте их через
`just spec-compile` / `uv run python -m ogip.spec_compile all` (сначала
`export UV_PROJECT_ENVIRONMENT=.run/venv`); один движок — через
`uv run python -m ogip.spec_compile <engine>`. `src/tests/unit/test_engine_projects_cover_spec.py`
— защита от дрейфа: тест падает, если в каком-либо закоммиченном снапшоте отсутствует модель,
объявленная в `spec/sql`, поэтому изменение `spec/sql` с забытой перегенерацией не может пройти
`make check`.

`transform/sqlmesh/models/` — исключение: он **в `.gitignore`, не коммитится**. SQLMesh —
продакшен-движок, и `pipelines/_shared/steps.py::build_warehouse` перекомпилирует его заново из
`spec/sql` непосредственно перед каждым реальным запуском, поэтому закоммиченного снапшота,
который мог бы дрейфовать, не существует — тот же тестовый файл защищает его иначе: прогоняет
живой компилятор `compile_to_sqlmesh` во временную директорию вместо проверки директории в
репозитории.

**Известный пробел — аудиты SQLMesh компилируются, но не выполняются `make check`.** Секции
`checks:` каждой модели `spec/sql` проецируются в клаузы SQLMesh `audits (...)` (`to_sqlmesh.py`),
но `make check` запускает `pytest -m "not integration and not e2e"`, который никогда не делает
plan/apply SQLMesh на реальном хранилище — поэтому дефолтный гейт эти аудиты никогда не
вычисляет. Реально их выполняет только
`uv run pytest src/tests/e2e/test_all_setups.py::test_base_setup_builds_and_produces_ml -k
sqlmesh` (помечен `e2e`, исключён из `make check`) или живой запуск `prefect-sqlmesh`.
Регрессия `not_null` может проскочить — и уже проскочила — мимо зелёного `make check`. См.
[ADR-0019](../docs/adr/ADR-0019-odts-dq-projection-and-seven-prefect-subprojects.md) и
[ODTS IMPLEMENTATION.md](../spec/ODTS/IMPLEMENTATION.md).

## Почему компилятор парсит SQL, а не сопоставляет строки

`src/ogip/spec_compile/dialect.py` (SQLGlot) выполняет работу, которая требует *понимать* SQL:
переписывает `staging.stg_games` → `{{ ref('stg_games') }}` только там, где это настоящая ссылка
на таблицу (regex переписал бы её и внутри строковых литералов), выводит lineage из SQL для
перекрёстной проверки написанного вручную `depends` и перенацеливает модель на другой диалект.
Последнее делает политику переносимого SQL ([AGENTS.md](../AGENTS.md), жёсткое правило 7;
собственный ADR-0016 OGAP выше по течению — не
[ADR-0016](../docs/adr/ADR-0016-odts-authoring-format-spec-sql.md) этого репозитория)
исполняемой — тестовый набор при каждом прогоне перенацеливает каждую spec-модель на
Postgres/ClickHouse/BigQuery.

Движко-специфичный SQL, когда без него не обойтись, живёт в `spec/sql/_ext/<engine>/` — никогда не здесь.
