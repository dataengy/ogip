<!-- ru-translation-of: docs/architecture/storage.md sha:31e0479ae7f8 -->
<!-- Автоперевод. Источник — docs/architecture/storage.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [storage.md](storage.md)

# Хранилище — озеро Parquet

> Область: где живёт сырой Parquet и как до него добирается пайплайн.
> Решения: [ADR-0003](../adr/ADR-0003-parquet-lake-defer-iceberg-ducklake.md) (озеро Parquet;
> Iceberg/DuckLake отложены) · [ADR-0002](../adr/ADR-0002-duckdb-analytical-engine.md) (DuckDB
> читает Parquet на месте) · D2 (профили хранилища).

## Один путь кода, четыре бэкенда

Озеро — это **обычный Parquet** (PyArrow, записывается через dlt). Где он приземляется — это
*профиль*, а не ветка кода:

| Backend | Что это | Endpoint | Стиль URL |
|---|---|---|---|
| `local` | **по умолчанию** — локальная файловая система под `.run/data/raw` | — (`file://`) | — |
| `minio` | S3-совместимый контейнер для локальной разработки / CI | `http://localhost:9000` | **path** |
| `s3` | AWS S3 | *пусто* → определяется по региону | virtual-host |
| `r2` | Cloudflare R2 — облако записи (D9) | `https://<account>.r2.cloudflarestorage.com` | virtual-host |

`minio`, `s3` и `r2` — это **один и тот же S3-путь кода** — различаются только endpoint,
учётные данные и стиль URL. В этом весь смысл ADR-0003: разрабатывать против MinIO бесплатно
и офлайн, затем нацелиться на R2 или S3 одними лишь учётными данными. Ничто в `ingestion/`,
`spec/` или потоке не меняется.

MinIO нужны URL в **path-style** (`endpoint/bucket/key`), потому что у него нет DNS-хостов для
бакетов; AWS и R2 используют дефолтный virtual-host стиль. `src/ogip/storage.py` это
обрабатывает.

## Шов

Всё это живёт в [`src/ogip/storage.py`](../../src/ogip/storage.py):

| Функция | Кем используется | Что делает |
|---|---|---|
| `raw_bucket_url(data_dir)` | писатели | `file://…` для `local`, иначе `s3://<raw_bucket>` |
| `dlt_filesystem_destination(data_dir)` | `ingestion/base/base_source.py` | назначение dlt, с прикреплёнными учётными данными |
| `configure_duckdb_s3(con)` | ad-hoc потребители DuckDB | загружает `httpfs` + регистрирует секрет S3, чтобы DuckDB читал `s3://` |

`configure_duckdb_s3` — **no-op на `local`** и идемпотентен, поэтому его безопасно вызывать
безусловно. Учётные данные передаются в DuckDB как **связанные параметры** — никогда не
интерполируются в SQL.

Это для соединений, которые открываем *мы* (ноутбуки, `dq/`). **SQLMesh не из их числа**: он
открывает собственное соединение, поэтому берёт S3 через свою конфигурацию — `extensions: [httpfs]`
плюс запись `secrets:` в `transform/sqlmesh/config.yaml`, интерполируемая из тех же слотов
`OGIP_S3_*`. `src/ogip/warehouse.py` не нуждается ни в чём: он читает собранное хранилище,
никогда не `s3://`.

## Конфигурация (SSoT)

Два слоя, согласно [`config/README.md`](../../config/README.md):

- **Какой** бэкенд → `config/config.yml → storage.backend`; переопределяется через
  `OGIP_STORAGE_BACKEND`. Никогда не редактируйте отрендеренный `.env` — редактируйте YAML и
  `make render-env`.
- **Где/как** → `OGIP_S3_*`: `ENDPOINT_URL`, `RAW_BUCKET`, `REGION` (производные от
  `config.yml`) плюс `ACCESS_KEY_ID` / `SECRET_ACCESS_KEY` (слоты секретов, пустые по умолчанию —
  заполняются вручную или секретами GitHub Actions, ADR-0011 / D10).

Ошибка конфигурации падает **рано и с объяснением**, а не как загадочный 403:
`minio` и `r2` без endpoint, либо любой объектный бэкенд без учётных данных вызывают
`StorageBackendError`, называя точную переменную для установки.

## Локальная разработка

```bash
make storage-up                      # MinIO + create the raw bucket; prints the dev keys
make test-integration                # round-trips real Parquet through MinIO
```

> **Статус — `local` сегодня единственный бэкенд, на котором работает пайплайн.** Шов, стек
> MinIO и round-trip тест готовы и зелены, но два production-места вызова ещё не подключены:
> `ingestion/base/base_source.py` по-прежнему нацелен на локальную ФС, а Layer-0
> (`spec/sql/raw/*.sql`) жёстко прописывает `read_parquet('.run/data/raw/…')` — так что SQLMesh
> продолжал бы читать локальную ФС независимо от того, что пишет dlt. Научить компилятор
> спецификации инъецировать корень озера — оставшийся блокер; отслеживается в
> [.ai/tasks/s3-object-storage.md](../../.ai/tasks/s3-object-storage.md). Установка
> `backend: minio` сегодня меняет только ingestion — не ждите зелёного `make run` пока.

Консоль MinIO: `http://localhost:9001` (dev-ключи `ogipminio` / `ogipminio123` — одноразовые
локальные литералы, **не** секреты). `make storage-down` останавливает её; том с данными
сохраняется.

Корневые учётные данные MinIO намеренно **отделены** от клиентских слотов `OGIP_S3_*` —
см. [deploy/README.md](../../deploy/README.md#credentials), почему.

## Раскладка

Неизменна между бэкендами — сдвигается только префикс:

```
<lake-root>/raw/<system>__<entity>/*.parquet     # Layer 0, 1:1 AS-IS
```

`<lake-root>` — это `.run/data` (local) или `s3://ogip-raw`. Партиционирование raw следует
`config.yml → raw.partitioning`; именование Layer-0 (`<system>__<table>`) — закон, см.
[overview.md](overview.md).

## Почему пока не табличный формат

Iceberg/DuckLake остаются исследованием (ADR-0003): обычный Parquet + DuckDB покрывают размеры
датасетов, на которые нацелена платформа, а табличный формат добавил бы каталог, задачи
обслуживания и историю миграции без нынешней выгоды. S3-путь кода здесь — тот же самый, который
понадобился бы миграции на Iceberg, так что ничто не закрыто.
