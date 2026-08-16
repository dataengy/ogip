<!-- ru-translation-of: docs/runbooks/run-pipeline.md sha:f70767e2fce6 -->
<!-- Автоперевод. Источник — docs/runbooks/run-pipeline.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [run-pipeline.md](run-pipeline.md)

# Ранбук — Запуск пайплайна (Docker + Prefect)

- **Триггер:** запустить ежедневный пайплайн, backfill или альтернативный `run-profile`.
- **Владелец:** любой контрибьютор / оператор.

## Предусловия

- Сервисы `make up` здоровы; `.env` отрендерен; ключи API источников присутствуют в `.env` для реального извлечения.

## Шаги

1. Выберите профиль (по умолчанию — production): `just run-profile prefect-sqlmesh`
   (альт.: `prefect-sql`, `prefect-bruin`, `prefect-dbt`, `prefect-sqlmesh-over-dbt`, `prefect-dagster-dlt-dbt`).
2. Разверните/запустите поток Prefect: `just prefect-deploy && just prefect-run ingest_transform_publish`
   (обёртка над `integrations/prefect/` — Prefect CLI/API).
3. Следите за запуском в UI Prefect (серверный профиль) или в логах потока (эфемерный).

## Проверка

- Состояние запуска Prefect = `Completed`; `.run/outputs/*.parquet` обновлены; гейт DQ пройден
  (`platform_meta.dq_results`); ноутбук / страница Evidence отображает новые данные.

## Откат

- Raw неизменяем — повторный запуск идемпотентен. Чтобы отбросить плохую сборку warehouse: `make warehouse-reset`.

## Эскалация

- Красный запуск → [pipeline-failure.md](pipeline-failure.md).
