<!-- ru-translation-of: docs/runbooks/run-dagster.md sha:4802ece96bcb -->
<!-- Автоперевод. Источник — docs/runbooks/run-dagster.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [run-dagster.md](run-dagster.md)

# Ранбук — запуск альт-оркестрации Dagster (dbt + dlt + ingestr CDC)

- **Триггер:** запустить или продемонстрировать комбо-профиль `prefect-dagster-dlt-dbt` ([ADR-0015](../adr/ADR-0015-dagster-alt-orchestration-dg-components.md)).
- **Владелец:** любой контрибьютор. **Путь:** `experimental/orchestration/dagster_ogip/` (самодостаточный uv-проект, вне продакшен-пути).

## Предусловия

- `uv`. Из директории проекта: `uv sync`. Без Docker для dev / демо-пути.
- dbt-проект в `dbt/` **генерируется из `spec/`** — никогда не правьте его руками. Он
  перегенерируется `e2e/run_combo.sh` и может быть перегенерирован вручную (см. ниже).

## Dev — интерактивно

```bash
cd experimental/orchestration/dagster_ogip
export DAGSTER_HOME="$PWD/deploy/dev"     # dagster.yaml must live in DAGSTER_HOME (SQLite storage)
uv run dg dev                              # UI at http://localhost:3000
```

## Запуск ассетов из CLI

```bash
uv run dg check defs                                   # validate components + defs
uv run dg launch --assets '*'                          # everything (needs a live PG for cdc_landing)
uv run dg launch --assets 'key:"rawg__games"+'         # dbt graph: raw → stg → core → fs (build = models + tests)
uv run dg launch --assets 'key:"game"+'                # only game + downstream — asset selection prunes the graph
```

`dbt build` запускает модели **и** сгенерированные dbt-тесты, так что DQ — часть того же запуска.

## End-to-end (источник → слой FS)

```bash
bash e2e/run_combo.sh     # compile spec→dbt · dlt ingest · dbt build+tests · assert fs.market_features
```

Это канонический комбо-e2e (также запускается GitHub-воркфлоу `dagster-e2e`). Он использует
демо-фикстуру RAWG и DuckDB — без Docker.

## Перегенерация dbt-проекта из spec

Предпочитайте `bash jobs/dg-tasks.sh update-dbt` (он подхватывает SSoT `DBT_PROJECT_DIR`). Ручной
эквивалент — расположение dbt-проекта берётся из `jobs/dbt-env.sh`, а не из захардкоженного `dbt`:

```bash
source jobs/dbt-env.sh   # DBT_PROJECT_DIR — SSoT for the generated project's location
PYTHONPATH=../../../src .venv/bin/python -c "
from pathlib import Path; import os; from ogip.spec_compile.to_dbt import compile_to_dbt
root=Path('../../..').resolve()
compile_to_dbt(root/'spec/sql', Path(os.environ['DBT_PROJECT_DIR']), warehouse=root/'.run/data/warehouse/ogip.duckdb', repo_root=root)"
```

## Сущности оркестрации (jobs · schedules · sensors · partitions)

Определены в `defs/orchestration/definitions.py`; детерминированная shell-работа — в `jobs/dg-tasks.sh`.

**Джобы** — *asset-джобы* (идиоматичная выборка): `raw_ingest_job` · `staging_job` · `core_job` ·
`fs_job` · `dwh_assets_job` (весь DWH) · `dlt_ingest_job` · `cdc_asset_job`. *Op-джобы* (явное
управление): `dwh_incremental_job` / `dwh_full_refresh_job` (полный vs инкрементальный) · `update_dbt_job`
(перегенерировать spec→dbt + parse) · `update_dbt_changed_job` (запускать только `state:modified+`) ·
`parsing_job` · `prefect_trigger_job` · `cdc_job` · `market_snapshot_job` (партиционированный).

**Расписания** — `daily_dwh_full_refresh` (3:00) · `hourly_dwh_incremental` · `quarter_hourly_cdc`
· `daily_dbt_subproject_update` (2:00) · `daily_raw_ingest` (1:30) · `daily_market_snapshot`
(партиционированное).

**Сенсоры** — `raw_landed_runs_dwh` (asset-сенсор: новый raw → обновить DWH) · `new_postgres_raw_data`
(строки в landing → инкрементальный запуск; пропускает без PG) · `spec_change_updates_dbt` (mtime
spec/sql → запуск изменённых моделей) · `dwh_run_failure_alert` (хук на падение запуска для lane
алертинга).

**Партиции + бэкфилы** — `market_snapshot` — ассет с **дневными партициями** (поддерживает бэкфил):

```bash
uv run dg launch --assets market_snapshot --partition 2026-07-15   # one partition
# range backfill: the Dagster UI "Backfill" button, or
uv run dagster asset backfill market_snapshot --partitions 2026-07-15,2026-07-16,2026-07-17
```

## Prod (на Postgres)

`deploy/prod/dagster.yaml` использует Postgres-хранилище через `env`-ссылки (без литералов
секретов). Реальному запуску нужны `DAGSTER_HOME`, указывающий на него, окружение `DAGSTER_PG_*`
и долгоживущие `dagster-webserver` / `dagster-daemon` (не `dg dev`). CDC дополнительно требует
`wal_level=logical` + `CREATE PUBLICATION ogip_landing_pub FOR TABLES IN SCHEMA landing` —
шаг DBA/VPS.

## Интеграция AI / MCP

**MCP — управление запущенным инстансом из агента.** [`dagster-mcp`](https://pypi.org/project/dagster-mcp/)
оборачивает Dagster GraphQL API (21 инструмент: runs, assets, jobs, schedules/sensors, `launch_job`,
`backfill_assets`, `reload_code_location`). Он объявлен здесь в `.mcp.json` и указывает на
вебсервер `dg dev`:

```jsonc
// .mcp.json → mcpServers.dagster → uvx dagster-mcp, DAGSTER_URL=http://localhost:3000
```

Сначала запустите `dg dev`, затем MCP-клиент (Claude Code / Cursor) подхватит `.mcp.json`. По
умолчанию он **read-only** (`DAGSTER_READ_ONLY=true`); переключите в `false`, чтобы разрешить
запуски/бэкфилы/терминирования. Проверено: `uvx dagster-mcp` устанавливается и стартует против
локального инстанса.

**Скиллы — строить Dagster быстрее.** [`dagster-io/skills`](https://github.com/dagster-io/skills) —
официальный пак Agent-Skills от Dagster (совместим с Claude Code / Cursor / Codex). Устанавливается
per-user, не в этот репозиторий:

```
/plugin marketplace add dagster-io/skills
```

**Config-driven Dagster (оценён, не принят):** см.
[docs/comparisons/dagster-odp-vs-spec-compiler.md](../comparisons/dagster-odp-vs-spec-compiler.md) —
dagster-odp пересекается с нашим SSoT spec→компилятора, поэтому остаётся референсом.

## Эскалация

- Застрявшие/стоящие в очереди запуски → скилл `/dagster-zombie-runs`. Инфраструктура (Postgres/Docker) → DevOps (отдельно).
