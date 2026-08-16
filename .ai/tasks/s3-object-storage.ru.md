<!-- ru-translation-of: .ai/tasks/s3-object-storage.md sha:8716dfe20dc0 -->
<!-- Автоперевод. Источник — .ai/tasks/s3-object-storage.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [s3-object-storage.md](s3-object-storage.md)

# Задача — S3-объектное хранилище (лейк-профили `minio` / `s3` / `r2`)

**Статус:** 🚧 в работе — шов, стек MinIO, тесты и документация завершены и проверены зелёными
против реального MinIO. Lane `core-pipeline` выведена из работы (2026-07-30): оставшиеся
call site'ы (4 пункта, настоящий — инъекция корня лейка на Layer-0) теперь едут в зонтичной задаче R2/VPS
[#17](https://github.com/dataengy/ogip/issues/17) — V2-скоуп плана финализации. `local`
остаётся дефолтом, так что ничто из существующего поведение не поменяло.

<!-- tasks-sync читает ТОЛЬКО эту строку Status, сопоставляя подстроки ("✅", "done", "shipped"),
     чтобы решить, закрывать ли issue. Не допускайте этих слов в прозе выше, пока матчер
     не заанкорен, иначе задача в работе снова будет закрыта как COMPLETED (уже было: #8). -->

Lane: `s3` (объект блокировки параллельных сессий). Скоуп: `src/ogip/storage.py`, MinIO в
`deploy/docker-compose.yml`, Makefile-таргеты `storage-*`, тесты и документация хранилища.
Решения: [ADR-0003](../../docs/adr/ADR-0003-parquet-lake-defer-iceberg-ducklake.md) (Parquet-лейк)
· D2 (профили хранилища) · архитектура:
[storage.md](../../docs/architecture/storage.md).

## Почему

`config/config.yml → storage.backend` объявлял `local | minio | s3 | r2`, и
`config/.env-render.py` уже рендерил `OGIP_STORAGE_BACKEND` в `.env` — но **никто ни то,
ни другое не читал**. `ingestion/base/base_source.py` жёстко задавал dlt destination как локальную
файловую систему (`bucket_url=data_dir.resolve().as_uri()`). D2 был документацией, а не поведением:
запустить OGIP против объектного хранилища было невозможно.

## Сделано

- **`src/ogip/storage.py`** — единый шов, разрешающий backend → URL бакета + креды:
  - `StorageSettings` — `OGIP_STORAGE_BACKEND`, дефолт читается из SSoT (без дублирования значения).
  - `raw_bucket_url(data_dir)` — `file://…` для `local`, иначе `s3://<raw_bucket>`. Чистая функция.
  - `dlt_filesystem_destination(data_dir)` — dlt destination с прикреплёнными кредами.
  - `configure_duckdb_s3(con)` — загружает `httpfs`, регистрирует S3-секрет через **связанные
    параметры** (креды никогда не попадают в текст SQL). No-op на `local`; идемпотентна.
  - Падает рано, называя конкретную отсутствующую переменную, вместо загадочного 403.
  - MinIO → path-style URL (у него нет DNS-style bucket-хостов); пустой endpoint → настоящий AWS.
- **`deploy/docker-compose.yml`** — базовый стек, на который Makefile уже ссылался, но которого
  никогда не существовало (`make up` был сломан): Postgres + Prefect, плюс `minio` + `minio-init`
  (bootstrap бакета) за профилем `storage`. Объявляет сеть `ogip`, которую ожидает `deploy/obs/`,
  и удовлетворяет preflight `deploy/vps/deploy.sh`.
- **`make storage-up` / `make storage-down`**; `deploy/README.md`.
- **Тесты** — 11 unit (разрешение бэкенда, стиль URL, ошибки кредов, no-op на `local`) +
  интеграционный **round-trip**-тест MinIO: dlt пишет Parquet в `s3://ogip-raw`, DuckDB читает
  каждую строку обратно через `httpfs`, и ничего не утекает на локальную ФС.
- **`docs/architecture/storage.md`** — модель одного код-пути, слои конфигурации, локальная разработка.

## Замечание по безопасности

Root-креды MinIO (`MINIO_ROOT_*`) намеренно **отделены** от клиентских слотов OGIP
(`OGIP_S3_*`). В клиентских слотах может лежать реальный ключ AWS/R2, а прописать реальный ключ в
локальный контейнер как его root-пароль — это footgun. Для профиля `minio` эти два набора должны совпадать;
они поставляются как одноразовые dev-литералы (`ogipminio` / `ogipminio123`) — никогда не секреты.

## Заблокировано

Все оставшиеся call site'ы живут в lane **`core-pipeline`**, удерживаемой параллельной сессией
(lock истекает 2026-07-17 16:00). Применить в этом порядке после освобождения:

1. **`ingestion/base/base_source.py`** — заменить жёстко заданный локальный destination на
   `dlt_filesystem_destination(data_dir)`; `run()` возвращает **URL** датасета (`str`), а не
   `Path`. Его единственный вызывающий (`pipelines/flows/main.py:41`) уже делает `str(out)`, так что
   флоу и его ключ ассета `file://ogip/raw/rawg__games` не затронуты.
2. **`spec/sql/raw/*.sql` + компилятор spec** — ⚠️ **настоящий end-to-end-блокер.** Layer-0
   жёстко задаёт локальный литерал:
   `select * from read_parquet('.run/data/raw/rawg__games/*.parquet')`. Объектному хранилищу нужен
   корень лейка, **инжектируемый компилятором** (например, переменная `@lake_root`) вместо
   литерального пути — иначе SQLMesh продолжает читать локальную ФС независимо от того, куда пишет dlt.
   Это забота spec-компилятора (D0/D5) и причина, по которой `backend: minio` пока не может прогнать
   `make run` end to end.
3. **`transform/sqlmesh/config.yaml`** — DuckDB gateway нуждается в доступе к S3. SQLMesh
   поддерживает это нативно (у `DuckDBConnectionConfig` есть и `extensions`, и `secrets`), так что это
   **конфигурация, а не код**: `extensions: [httpfs]` + запись `secrets:`, интерполируемая из
   env-слотов `OGIP_S3_*`. SQLMesh открывает собственное соединение, поэтому `configure_duckdb_s3()`
   до него не дотянется.
4. **`config/.env-render.py`** — поставлять `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` плюс
   соответствующие dev-дефолты `OGIP_S3_*` как `DEMO_DEFAULTS` (существующий паттерн
   `OGIP_PG_PASSWORD`), чтобы `make storage-up` + `backend: minio` работали из голого checkout
   без ручного заполнения слотов.

`src/ogip/warehouse.py` **не** требует изменений: `export_table` читает из собранного DuckDB-warehouse
и никогда не трогает `s3://`.

## Открытый вопрос — у `configure_duckdb_s3()` пока нет продакшен-вызывающего

Правило 2 AGENTS гласит: никакой абстракции без двух конкретных call site'ов. Сегодня у `configure_duckdb_s3`
их **ноль**: SQLMesh конфигурирует своё соединение сам (пункт 3 выше), а `warehouse.py` никогда
не читает `s3://`. Сейчас её используют только тесты. Она сохранена, потому что
[ADR-0002](../../docs/adr/ADR-0002-duckdb-analytical-engine.md) обещает, что DuckDB читает Parquet
на месте из S3/R2, а ad-hoc-потребители, которым она нужна, уже запланированы — ноутбуки
(D7, основной DS-интерфейс) и раннер `dq/` (Фаза 4). **Если они не материализуются —
удалить её**, а не давать ей гнить.

## Верификация

`ruff` чистый · `pyright` strict 0 ошибок · 13/13 storage-тестов зелёные, включая round-trip
MinIO против живого контейнера (`make storage-up`).

## Далее

- Применить подготовленную core-обвязку, когда `core-pipeline` освободится; затем прогнать полный пайплайн с
  `backend: minio` end to end (`make run`) и добавить e2e-проверку.
- Подключить R2 как cloud of record (D9) — только креды; изменений кода не ожидается.
- Рассмотреть CI-интеграционную джобу с сервис-контейнером MinIO (round-trip-тест уже
  имеет CI-форму: он чисто пропускается при отсутствии MinIO).
