<!-- ru-translation-of: .ai/tasks/r2-vps-finalize.md sha:0ba1bb3d952f -->
<!-- Автоперевод. Источник — .ai/tasks/r2-vps-finalize.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [r2-vps-finalize.md](r2-vps-finalize.md)

# Задача — Финализировать R2-лейк + VPS-деплой (закрыть подготовленные хендоффы s3/vps)

**Статус:** 📋 готово к работе — все предпосылки подготовлены; все оставшиеся правки лежат в одной lane ·
**Приоритет:** **P1**

Lane: `core-pipeline` (её прежний lock устарел — см. аудит lock'ов в STATUS; сбросить и
захватить заново). Зонтичная задача над *оставшимися* пунктами
[s3-object-storage.md](s3-object-storage.md) и
[vps-deploy-tooling.md](vps-deploy-tooling.md) — детали и история остаются в тех файлах;
этот фиксирует порядок выполнения.

## Почему

Шов хранилища (`src/ogip/storage.py`, round-trip через MinIO доказан) и VPS-инструментарий
(`deploy/vps/*`, проверен в dry-run) существуют, но пайплайн по-прежнему работает только на локальной ФС,
а реальный деплой останавливается на preflight. Закрытие этой задачи делает заявленную облачную историю
(R2 как cloud of record — D2/D9) и историю деплоя истинными от начала до конца.

## Порядок работ

1. [ ] `ingestion/base/base_source.py` — заменить жёстко заданный локальный dlt destination на
       `dlt_filesystem_destination(data_dir)`; `run()` возвращает URL датасета (`str`).
       _Координация: этот файл перешёл в lane `ingestion` при разделении скоупа 2026-07-17._
2. [ ] Компилятор spec + `spec/sql/raw/*.sql` — инжектировать корень лейка (из
       `ogip.storage.raw_bucket_url()`) вместо литерального пути `.run/data/...` —
       **настоящий блокер** для любого нелокального бэкенда.
3. [ ] `transform/sqlmesh/config.yaml` — DuckDB gateway: `extensions: [httpfs]` +
       `secrets:`, интерполируемые из слотов `OGIP_S3_*` (конфигурация, а не код).
4. [ ] `config/.env-render.py` — root MinIO + dev-дефолты `OGIP_S3_*` в `DEMO_DEFAULTS`
       (существующий паттерн `OGIP_PG_PASSWORD`), чтобы голый checkout запускал `backend: minio`.
5. [ ] Проверить: `make run` зелёный с `backend: minio` локально + e2e-проверка; добавить
       CI-интеграционную джобу с сервис-контейнером MinIO (round-trip-тест уже чисто
       пропускается при отсутствии MinIO).
6. [ ] **R2** — создать бакет, заполнить слоты `OGIP_S3_*` эндпоинтом/кредами R2
       (код-путь идентичен `s3`); зафиксировать в
       [docs/architecture/storage.md](../../docs/architecture/storage.md).
7. [ ] `integrations/prefect/{deploy,trigger}.py` — разблокирует `just prefect-deploy`,
       шаг 5 `deploy/vps/deploy.sh` и `deploy/vps/smoke.sh`.
8. [ ] Направить `config/config.yml → deploy.vps.host` на реальную машину; прогнать
       `just vps-provision → vps-deploy → vps-smoke` от начала до конца.
9. [ ] Находясь в этой lane, по возможности закрыть два obs-хендоффа (лог-файл флоу + маппинг
       obs-портов — STATUS «Handoffs»), чтобы задеплоенная машина была наблюдаемой с первого дня.

## Приёмка

- `make run` зелёный с `backend: r2` (реальный бакет) с ноутбука: raw Parquet приземляется в
  R2, и SQLMesh читает его обратно через httpfs.
- `just vps-deploy && just vps-smoke` зелёные против реального хоста.
- `make check` + CI зелёные; секции хендоффов s3/vps в STATUS схлопываются в закрытые.
