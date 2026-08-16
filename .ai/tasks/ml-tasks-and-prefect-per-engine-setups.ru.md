<!-- ru-translation-of: .ai/tasks/ml-tasks-and-prefect-per-engine-setups.md sha:bec3805eb38f -->
<!-- Автоперевод. Источник — .ai/tasks/ml-tasks-and-prefect-per-engine-setups.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ml-tasks-and-prefect-per-engine-setups.md](ml-tasks-and-prefect-per-engine-setups.md)

# Задача — ML-фиче-задачи + раздельные per-engine сетапы Prefect + Dagster-из-Prefect

**Статус:** 🟢 отгружено — у каждого сетапа SQL-тула есть собственный Prefect-флоу, он выполняет
шаг ML-фич и покрыт e2e; `log` — домашний алиас логгера; Makefile — лаунчер пайплайна.

## Сделано

- **Задачи ML-фиче-инжиниринга** (`experimental/python_tasks/tasks.py`): стандартизация, min-max,
  винзоризация выбросов, взаимодействия, квантильное бакетирование, one-hot (+top-n), когортные
  фичи года релиза, детерминированный leakage-safe train/test-сплит, сборщик матрицы фич — все чистые.
- **Типизированная граница** (`experimental/python_tasks/pipeline.py`): `build_ml_features(warehouse,
  outputs_dir) -> dict[str, int]` читает `core.game`, запускает задачи, пишет
  `ml_features/ml_train/ml_test.parquet`. Датафреймы никогда не пересекают границу в pyright-strict-код.
- **Раздельные per-engine сетапы Prefect** (`pipelines/flows/engines/`): один модуль флоу на SQL-тул —
  `prefect_{sqlmesh,sql,dbt,opendbt,sqlmesh_dbt,bruin}.py` — каждый самодостаточный сетап
  с ассетами `@materialize` (lineage в неймспейсе движка), общая логика шагов в `_common.py`
  (`make_engine_flow`). Каждый сетап выполняет ingest → transform → **ML** → publish.
- **Dagster-из-Prefect** (`prefect_dagster.py`, профиль `prefect-over-dagster`): Dagster владеет
  dlt+dbt (`dg launch`), Prefect владеет ML + publish + алертингом. Скилл: `dagster-from-prefect`.
- **Реестр + диспатч**: `engines/__init__.py:ENGINE_FLOWS`; `run-profile.py` запускает
  per-engine флоу; `main.py` реэкспортирует SQLMesh-флоу как `ingest_transform_publish` (обратная совместимость).
- **E2E** (`src/tests/e2e/test_all_setups.py`): базовые движки — всегда; тяжёлые движки + Dagster — за
  `OGIP_E2E_ALL_ENGINES=1`. Проверено: plain_sql + sqlmesh собирают и производят ML end-to-end.
- **Алиас `log`**: `ogip.logger` экспортирует `log` (домашний алиас); все 16 модулей мигрированы
  `logger` → `log`. Конвенция задокументирована (AGENTS.md, скилл `use-log-alias`, память проекта).
- **Фикс раннера**: plain-SQL-раннер теперь удаляет объект несовпадающего типа (SQLMesh-view против
  таблицы) перед пересборкой — движки сравнения делят один warehouse.

## Проверено

`make check` зелёный (ruff, pyright strict 0, pytest). E2e базовых движков зелёный. ML-граница
протестирована на реальной фикстуре RAWG (матрица на 5 строк, 8 фич + метка).
