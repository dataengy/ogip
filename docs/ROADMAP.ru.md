<!-- ru-translation-of: docs/ROADMAP.md sha:52ddd554b96d -->
<!-- Автоперевод. Источник — docs/ROADMAP.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ROADMAP.md](ROADMAP.md)

# OGIP — Дорожная карта

Поэтапная поставка с **воротами одобрения пользователем после каждой фазы**. Полная детализация
и критерии приёмки — в [.ai/PLAN.md](../.ai/PLAN.md); здесь — обзорная карта. Неизвестные
требования, влияющие на эту карту, — в [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md).

> **Идёт финализационный прогон (2026-07-30)** — действующий план:
> [superpowers/plans/2026-07-30-finalization-land-everything.md](superpowers/plans/2026-07-30-finalization-land-everything.md)
> (три зелёные команды запуска → re-root T4–T9 → приземлить все lane → dev→main). Таблица
> приоритетов ниже составлена до него и сохранена для контекста; статусы в карте фаз обновляются
> на шаге 21 финализации. Замороженные фичи: [реестр техдолга](techdebt/finalization-tbd.md).

## Текущие приоритеты (переприоритизировано 2026-07-17)

| # | Пункт | Lane | Детали |
|---|---|---|---|
| **P1** | **Слайс устойчивого скрейпинга** — асинхронный `ScraperSource` ([ADR-0014](adr/ADR-0014-resilient-scraping-concurrency.md)) + Postgres landing + первый скрейп-источник (HLTB) end-to-end | `ingestion` | [.ai/tasks/scraping-resilient.md](../.ai/tasks/scraping-resilient.md) |
| **P1** | **Финализировать R2 + деплой на VPS** — закрыть подготовленные хендоффы s3/vps: точки вызова storage-seam, корень лейка spec-компилятора, `integrations/prefect/deploy.py`, реальный бакет R2, деплой на хост + smoke | `core-pipeline` | [.ai/tasks/r2-vps-finalize.md](../.ai/tasks/r2-vps-finalize.md) |
| P2 | **Бэклог источников** — кандидаты, сопоставленные моделям игрового рынка (ценообразование · масштаб · бюджет · трекшн · качество) | backlog | [.ai/tasks/sources-backlog.md](../.ai/tasks/sources-backlog.md) |
| P2 | **Демо интеграции Python-задач** — задачи ML-подготовки на pandas/Polars поверх данных RAWG/core, готовые к будущему адаптеру SQL-transform-инструмента | experimental | [.ai/tasks/python-task-integration.md](../.ai/tasks/python-task-integration.md) |
| mid | Семантический слой `spec/` (engine-agnostic, формат Bruin) | `spec` | [.ai/tasks/spec-semantic-layer.md](../.ai/tasks/spec-semantic-layer.md) |
| then | M1–M4 — воспроизвести слайс M0 на альтернативных тулсетах (bruin · dbt · sqlmesh-over-dbt · dagster) — *понижено ниже P1* | `core-pipeline` / `dagster` | [.ai/PLAN.md](../.ai/PLAN.md) |

## Карта фаз

| Фаза | Результат | Статус |
|---|---|---|
| 0 | **Каркас и идентичность** — git init, pyproject (uv), тулинг, config SSoT, секреты, CI, task-sync + TODO | ✅ поставлено |
| M0 | **Ходячий скелет** — RAWG → dlt raw → SQLMesh (из spec) → ML parquet + ноутбук, на Prefect; e2e в CI | ✅ поставлено (CI 7/7) |
| 1 | **SSoT `spec/`** — контракты ODCS + портируемый SQL в формате Bruin (вкл. `fs/`) + DQ + lineage | 🟡 только слайс M0 |
| 2 | **Инжест (dlt) + Steam/RAWG** — `BaseSource`→dlt; Postgres `landing` + **скрейпинг ([ADR-0014](adr/ADR-0014-resilient-scraping-concurrency.md))** | 🟡 RAWG поставлен; **скрейпинг = P1** |
| 3 | **Трансформации (dbt primary + Bruin co-primary, ADR-0020)** — spec-компилятор → проекты движков на DuckDB, `raw→stg→core→fs` | ✅ primary-движки зелёные E2E; слои star/am/marts впереди |
| 4 | **Качество данных** — проверки spec → тесты движков (ADR-0019) + policy-мониторы (row-count, freshness), исполняемые `dq/run.py` | 🟡 исполнитель поставлен 2026-07-30; запись результатов → V2 |
| 5 | **ML-ready выходы + ноутбуки** — 6 `*.parquet` (marts + FS); DATASETS.md; демо в JupyterLab | 🟡 2 выхода + 1 ноутбук (M0) |
| 6 | **Оркестрация (Prefect) + Postgres** — сквозной `make run`; `platform_meta`; профили ephemeral + server | 🟡 ephemeral-флоу поставлен; профиль server + `platform_meta` впереди |
| 7 | **Наблюдаемость** — VictoriaMetrics + Loki + Alloy + Grafana; абстракция алертов | 🟡 стек + `Notifier` поставлены; инструментирование пайплайна впереди |
| 8 | **Остальные источники + облачное хранилище** — Steam Reviews, IGDB, Reddit, Twitch, HLTB, Metacritic; профили R2/MinIO/S3 | 🟡 storage seam + MinIO поставлены; **финализация R2 = P1**; источники → [бэклог](../.ai/tasks/sources-backlog.md) |
| 9 | **Сравнения + запускаемые профили + исследования** — 8 профилей запуска (3 primary + 5 с флагом experimental); анализы feature-store-инструментов + Evidence | 🟡 профили поставлены; исследовательские треки открыты |
| 10 | **Деплой на VPS + README + полировка** — ручной ранбук VPS (DevOps отдельно); README «от результата»; финальный аудит | 🟡 тулинг `deploy/vps/` поставлен; **реальный деплой на хост = P1** |

**Быстрый слайс (D4):** фазы 0–6 на **Steam + RAWG** дают работающее сквозное демо
`sources → raw → SQL → ML parquet`; наблюдаемость, остальные источники и экспериментальные
профили наслаиваются потом.
