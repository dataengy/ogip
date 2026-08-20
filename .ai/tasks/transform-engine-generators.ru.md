<!-- ru-translation-of: .ai/tasks/transform-engine-generators.md sha:3c914f5231e8 -->
<!-- Автоперевод. Источник — .ai/tasks/transform-engine-generators.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [transform-engine-generators.md](transform-engine-generators.md)

# Задача — Transform-сетапы как генераторы из `spec/sql` (движки сравнения A12)

**Статус:** 🟢 отгружено — каждый сетап `transform/` генерируется из единого `spec/sql`;
AST-слой на SQLGlot заменяет переписывание ссылок текстовой подстановкой; кросс-движковый паритет — гейт.

## Что

Заполнить `transform/` согласно его README и матрице профилей запуска (AGENTS.md → «Run & orchestration
profiles»): каждый недефолтный transform-сетап — это **генератор из `spec/sql`** (формат
Bruin-ассетов, SSoT — [ADR-0005](../../docs/adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md)), никогда
не рукописный. Продакшен остаётся на **SQLMesh** ([ADR-0004](../../docs/adr/ADR-0004-sqlmesh-default-transform-engine.md)).

## Сделано

- **`src/ogip/spec_compile/dialect.py`** — слой SQLGlot. Парсит SQL спецификации в AST для:
  переписывания ссылок (только настоящие ссылки на таблицы, никогда внутри строковых
  литералов/комментариев — та самая регрессия, которую даёт regex), lineage, выводимого из SQL
  (сверяется с рукописным `depends`), и перенацеливания диалекта (`transpile`) — политика
  переносимого SQL, ставшая исполняемой.
- **Генераторы** (все в `src/ogip/spec_compile/`): `to_sqlmesh` (существующий, продакшен) ·
  `to_dbt` (существующий; переписывание ссылок теперь на AST) · `to_sqlmesh_dbt` (**новый** — dbt-проект +
  `config.py` для dbt-загрузчика SQLMesh, состояние вне хранилища) · `to_bruin` (**новый** — дословный
  проброс, поскольку спецификация *и есть* Bruin, + каркас проекта).
- **`__main__.py`** — `just spec-compile [engine]` перегенерирует `transform/{sqlmesh,dbt,sqlmesh_dbt,bruin}/`.
- **`transform/runner.py`** — раннер plain-SQL (`prefect-sql`): топологическая сортировка `depends`,
  `create or replace` на DuckDB, без фреймворка.
- **`transform/engines.py`** — лончер: перегенерировать проект движка из `spec/`, затем запустить его.
- **OpenDBT** (`prefect-opendbt`) — тот же сгенерированный dbt-проект, прогоняемый через **OpenDBT**
  (расширенный dbt-core: модели local-python/DLT, кросс-проектные mesh-ссылки, кастомные адаптеры).
  Собственная dep-группа `opendbt` (объявлена конфликтующей с `engines`): OpenDBT 0.14 пинит dbt <1.10
  и требует sqlglot <30, поэтому резолвится отдельно. Генерируется с `with_packages=False` — отслеживаемые
  нами версии с hub отказываются ставиться под dbt 1.9. Проверено: паритет с plain-SQL OK.
- **`src/scripts/run-profile.py`** — разрешает `config/config.yml → run_profiles` и запускает
  flow с движком профиля; профиль Dagster указывает на его собственный проект.
- **`pipelines/flows/main.py`** — параметр `transform_engine` протаскивает движок профиля через
  flow; дефолтный путь никогда не покидает SQLMesh.
- **`src/scripts/spec-compile-verify.py`** (`just spec-verify`) — **гейт кросс-движкового паритета**:
  каждый сгенерированный движок собирает ОДИН И ТОТ ЖЕ `fs.market_features` из единой спецификации,
  с diff'ом против эталона plain-SQL. Проверено: plain_sql / dbt / bruin побайтово идентичны (5/5 строк).

## Проверено

`make check` зелёный (ruff, pyright strict 0, pytest). Каждый движок прогнан end-to-end на реальной
raw-фикстуре RAWG: plain_sql, dbt (`PASS=83`), bruin (`4 succeeded, 9 quality checks`),
SQLMesh-поверх-dbt (план применён, виртуальный слой обновлён). `test_spec_compile.py` закрепляет
контракты, включая перенацеливание каждой модели на Postgres/ClickHouse/BigQuery.

## Замечание про OGAP

OGAP (`../Hushcrasher/`) вручную сопровождает `dwh/engines/*` с дисциплиной переносимого SQL на
**макросах** (`ogap_hash_key()`, `ogap_config()`) — без генератора. OGIP **генерирует** то, что OGAP
писал руками; замысел макро-переносимости сохранён транспайл-тестами.
