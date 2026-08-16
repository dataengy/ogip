<!-- ru-translation-of: .ai/tasks/dagster-setup.md sha:348d93cc0378 -->
<!-- Автоперевод. Источник — .ai/tasks/dagster-setup.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [dagster-setup.md](dagster-setup.md)

# Задача — Настройка Dagster (dg CLI + Components, dev + prod)

**Статус:** 🟡 в работе — компоненты dbt + dlt отрабатывают зелёным; конфиги dev/prod на месте; ingestr CDC в ожидании.

Альтернативный полный сетап для профиля `prefect-dagster-dlt-dbt` (A12) — **вне
продакшен-пути** (ADR-0007). Живёт в `experimental/orchestration/dagster_ogip/` как
самодостаточный uv-проект, так что зависимости Dagster никогда не касаются продакшен-окружения.

## Установленные факты (проверено, а не предположено)

- **«Dagster 4» не существует** — последняя версия на PyPI — **1.13.14**; `dagster-dbt`/`dagster-dlt`/
  `dagster-postgres` — 0.29.14, `dagster-dg-cli` — 1.13.14. Современный подход —
  **`dg` CLI + Components**, его мы и используем.
- Заскаффолжено настоящим CLI: `uvx -U create-dagster project`, затем
  `dg scaffold defs dagster_dbt.DbtProjectComponent dbt_ingest` и
  `dg scaffold defs dagster_dlt.DltLoadCollectionComponent dlt_ingest`.

## Сделано

- **Компилятор spec → dbt** (`src/ogip/spec_compile/to_dbt.py`) — `DbtProjectComponent` требует
  настоящий dbt-проект, но SSoT остаётся `spec/` (ADR-0005), поэтому мы его генерируем:
  schema-qualified зависимости Bruin → `{{ ref() }}`, `tags:` Bruin → теги в конфиге dbt (именно
  это заставляет работать `select: 'tag:daily'`), колоночные `checks` Bruin → dbt-тесты в
  `schema.yml`. Пути времени выполнения абсолютизируются — dbt исполняется из каталога
  dbt-проекта, так что spec'овские repo-relative `.run/…` иначе молча резолвились бы в никуда.
- **dbt-компонент** — `defs/dbt_ingest/defs.yaml`: `project: "{{ project_root }}/dbt"`,
  `select: "tag:daily"`. Манифест dbt становится ассетами Dagster.
- **Нативный dlt-компонент** — `defs/dlt_ingest/{defs.yaml,loads.py}`: RAWG → сырой Parquet,
  тот же контракт Layer-0, что и в lane Prefect, так что dbt'шный `raw.rawg__games` читает
  идентичные данные.
- **dev** (`deploy/dev/dagster.yaml`) — SQLite в `DAGSTER_HOME`, `DefaultRunCoordinator`, без инфраструктуры.
- **prod** (`deploy/prod/dagster.yaml`) — хранилище Postgres **только через env-refs** (ADR-0011),
  `QueuedRunCoordinator`, ретеншен. Переиспользует платформенный Postgres (ADR-0008) на
  собственной БД.

## Проверено

- `dg check defs` → "All component YAML validated successfully. All definitions loaded successfully."
- `dg launch --assets '*'` → **RUN_SUCCESS**; `dbt build --select tag:daily`; PASS=12 ERROR=0
  (3 таблицы + 1 view + **8 data-тестов, сгенерированных из Bruin-checks**).
- **Выбор ассетов обрезает граф**: `dg launch --assets 'key:"game"+'` → Dagster скомпилировал это
  в `dbt build --select ogip.fs.market_features ogip.core.game` — PASS=7, а не 12.
- Граф ассетов охватывает обе интеграции: `raw/rawg__games` (dlt, группа `ingestion`) → `stg_games`
  → `game` → `market_features` (dbt).

## ingestr CDC (сделано)

Один пайплайн использует **CDC**, и это намеренно (D11): зона Postgres `landing` (куда
непрерывно пишут скрейперы) захватывается логической репликацией через **ingestr**, а батчевые
API-источники остаются на dlt.

- `cdc/ingestr_cdc.sh` — `ingestr ingest` с source-URI слота репликации/публикации,
  `--incremental-strategy merge`, `--stream` для непрерывного режима. Конфиг только из `OGIP_*` env
  (ADR-0011); печатаемая команда **скрывает пароль**. Проверено через `--dry-run` (без живого PG).
- `defs/cdc_ingest/definitions.py` — оборачивает это в ассет `cdc_landing` (kinds `ingestr`/
  `postgres`, группа `ingestion`), так что CDC сидит в одном графе с dlt-загрузкой + dbt-моделями.
- `dg check defs` зелёный со всеми четырьмя частями; `dg list defs` показывает `cdc_landing`.

## Комбо-e2e (сделано)

`e2e/run_combo.sh` прогоняет **весь пайплайн через Dagster** — SOURCE → FINAL LAYER на комбо
`dagster-dlt-dbt` (оркестратор Dagster · инжест dlt · трансформации dbt · dq — dbt-тесты):
компиляция `spec/`→dbt → `dg launch` dlt-инжеста → `dg launch` dbt build (модели **+** тесты) →
assert по `fs.market_features` (rows>0, фичи без null). Зелёный: `PASS=12`, `rows=5, nulls=0`.
Его гоняет отдельный GitHub-workflow **`dagster-e2e`** (вложенный uv-проект; не входит в основной `ci.yml`).
`tests/test_e2e_combo.py` — обёртка `pytest -m e2e`. Документация: [ADR-0015](../../docs/adr/ADR-0015-dagster-alt-orchestration-dg-components.md),
[ранбук](../../docs/runbooks/run-dagster.md).

Фиксы, найденные по пути к зелёному: dagster-dlt по умолчанию писал JSONL (запинили
`file_format="parquet"` на ресурсе + добавили pyarrow); DuckDB не создаёт родительский каталог
(`mkdir -p`); dbt сплющивал слои в `main` (добавили `schema=<layer>` + макрос
`generate_schema_name`), а ключ dbt-модели `raw` конфликтовал с dlt-ассетом (оставили `raw`
без квалификации схемой — это лишь регистрационная view).

## AI / MCP / тулинг (сделано — оценено на реальных фактах)

- **Dagster MCP** — подключили `dagster-mcp` (0.6.0) через `.mcp.json` → к запущенному `dg dev` (:3000),
  21 тул, по умолчанию read-only. Проверено, что ставится и стартует. Агенты теперь могут
  инспектировать/запускать/бэкфиллить инстанс через MCP.
- **dagster-io/skills** — официальный пак Agent-Skills; ставится per-user через маркетплейс
  плагинов Claude (`/plugin marketplace add dagster-io/skills`), сюда не коммитится. Отмечено в ранбуке.
- **dagster-odp** — оценён (config-driven фреймворк для Dagster, PyPI 0.1.4). **Не принят** — он
  пересекается с нашим SSoT spec→компилятор и специфичен для Dagster. Сохранён как
  [docs/comparisons/dagster-odp-vs-spec-compiler.md](../../docs/comparisons/dagster-odp-vs-spec-compiler.md).

## Дальше

- Проверить **prod** + живой CDC-прогон по-настоящему: нужен Docker/Postgres с `wal_level=logical` +
  `CREATE PUBLICATION ogip_landing_pub FOR TABLES IN SCHEMA landing` (в этом окружении недоступно).
- Подключить `just run-profile prefect-dagster-dlt-dbt` к этому проекту.
- Сгенерированный `dbt/` — артефакт сборки (в gitignore) — перегенерируется компилятором.
