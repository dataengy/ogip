<!-- ru-translation-of: .ai/tasks/m0-walking-skeleton.md sha:6c65a5d2884d -->
<!-- Автоперевод. Источник — .ai/tasks/m0-walking-skeleton.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [m0-walking-skeleton.md](m0-walking-skeleton.md)

# Задача — M0: «ходячий скелет» (RAWG → ML-выходы, на Prefect+dlt+SQLMesh)

**Статус:** ✅ сделано — пайплайн работает end-to-end; `make check` зелёный; e2e зелёный локально + в CI; CI 7/7.

## Сделано

- **Инжест (dlt):** `ingestion/base/` (BaseSource/ApiSource/ScraperSource) + `ingestion/sources/rawg.py`.
  Складывает сырой Parquet `raw/rawg__games/*.parquet` (Layer-0 `<system>__<table>` + `_ingested_at`/`etl_batch_id`).
  Демо-режим = синтетическая фикстура (`ingestion/samples/`, помечена); live = httpx+tenacity → dlt при заданном `RAWG_API_KEY`.
- **Spec (SSoT):** `spec/contracts/rawg/rawg__games.odcs.yaml` (ODCS) + SQL в формате Bruin
  `spec/sql/{raw,staging,core,fs}` (raw view → stg_games → game → market_features).
- **Трансформации (SQLMesh):** `src/ogip/spec_compile/` (тонкий компилятор Bruin→SQLMesh) + `transform/sqlmesh/config.yaml`
  (шлюз DuckDB). `src/ogip/warehouse.py` экспортирует relations → Parquet.
- **Оркестрация (Prefect):** `pipelines/flows/main.py` — `ingest_transform_publish` (эфемерно, без Docker).
- **Выходы:** `.run/data/outputs/{games,market_features}.parquet` (по 5 строк). Демо-ноутбук `notebooks/01_explore_datasets.ipynb`.
- **Тесты:** `src/tests/e2e/test_pipeline.py` запускает Prefect-джобу + проверяет выходы (D17). Добавлена CI-джоба `e2e`.

## Проверено

- Локально: `make run` → выходы; `make test-e2e` проходит (23 с); `make check` зелёный (pyright 0 ошибок, 6 юнит + 1 e2e).
- Удалённо: запушено в `dataengy/ogip`; CI зелёный 7/7 (lint·typecheck·test·**e2e**·bash-lint·structure-validate·secret-scan).

## Заметки / follow-up'ы

- Docker недоступен в этом окружении → Prefect запускался **эфемерно** (путь `make up` с Postgres/сервером — для M1+).
- Упомянутые, но ещё не построенные хвосты (неблокирующие): `just capture-sample`, деплой/триггер `integrations/prefect/`,
  `src/scripts/run-profile.py`, каркас Evidence (`experimental/bi/evidence/`). Строить вместе с M1–M4.

## Дальше → M1–M4

Реплицировать срез RAWG→выходы на альтернативных тулсетах (prefect-bruin, prefect-dbt, prefect-sqlmesh-over-dbt,
prefect-dagster-dlt-dbt); добавить визуализатор Evidence; затем расширяться (больше источников, слои star/am, DQ, наблюдаемость).
