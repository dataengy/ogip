# ODOS 0.1 — the OGIP implementation, described

[`examples/`](examples/README.md) is the normative six-group conformance model. This document
anchors every object in those fixtures to the code that implements it today:
[`experimental/orchestration/dagster_ogip/`](../../experimental/orchestration/dagster_ogip/README.md)
(the Dagster projection) and [`pipelines/flows/`](../../pipelines/flows/) (the Prefect
projection) — both currently hand-written. The ODOS compiler
([#37](https://github.com/dataengy/ogip/issues/37)) will generate both sides from lowercase
`spec/orchestration/`; until then this mapping is the review checklist for *"do the fixtures
still describe reality?"*.

## Status at a glance

| ODOS layer | State |
|---|---|
| Task registry (`registry: ogip.tasks`) | **live** — [`src/ogip/tasks/`](../../src/ogip/tasks/), ten `@odos_task` entries |
| Dagster projection | hand-written — `defs/orchestration/<group>/definitions.py`, six groups |
| Prefect projection | hand-written — `make_engine_flow` in [`pipelines/flows/_common.py`](../../pipelines/flows/_common.py) + one module per engine |
| The design's §2 drift (`ensure_raw`) | **resolved at the task layer** — both lanes call the same registry callables |
| Compiler, adapters, equivalence test | not built — the remaining scope of [#37](https://github.com/dataengy/ogip/issues/37) |

## 1. The task registry

`_defaults.yml` declares `registry: ogip.tasks`. Every name below resolves to a plain typed
function under [`src/ogip/tasks/`](../../src/ogip/tasks/), registered with
`@odos_task("<name>")` ([`_registry.py`](../../src/ogip/tasks/_registry.py)) and callable from
the CLI as `python -m ogip.tasks <name> --flag=value`.

| Registry name | Module | Consumed by |
|---|---|---|
| `dbt.build` | `tasks/dbt.py` | Dagster `build-dwh`, `build-dwh-full`, `dbt-evaluate`, `update-dbt-changed`; Prefect `build_warehouse("dbt")` |
| `dbt.parse` | `tasks/dbt.py` | Dagster `update-dbt` |
| `dbt.deps` | `tasks/dbt.py` | Dagster `dbt-deps` |
| `ingest.rawg` · `ingest.metacritic` · `ingest.all` | `tasks/ingest.py` | Prefect `_ingest` step (`ingest_raw = ingest_all`) |
| `ingest.parse_to_landing` | `tasks/ingest.py` | Dagster `parsing` |
| `cdc.catchup` | `tasks/cdc.py` | Dagster `cdc [--dry-run\|--stream]` |
| `integrations.trigger_prefect` | `tasks/integrations.py` | Dagster `prefect` |
| `snapshot.write` | `tasks/snapshots.py` | CLI only today — see §3 snapshots |

The Dagster side reaches the registry through
[`jobs/dg-tasks.sh`](../../experimental/orchestration/dagster_ogip/jobs/dg-tasks.sh), whose nine
tasks are now **thin aliases** (`ogip_task() { … python -m ogip.tasks "$@"; }`); the Prefect side
imports the same functions directly. This is what dissolved the governing design's §2 drift:
"ensure raw" no longer exists as a task on either side — the Dagster asset graph expresses
`raw → dbt`, and the Prefect flow runs `ingest.all` as an explicit first step.

Names the fixtures reference that are **not yet registry entries** (bodies still live inline):

| Fixture name | Where the body lives today |
|---|---|
| `checks.market_features_nonempty` | `market_features_check` in `defs/orchestration/warehouse/definitions.py` |
| `sensors.landing_rowcount` | `new_postgres_raw_sensor` in `defs/orchestration/warehouse/definitions.py` |
| `sensors.spec_sql_mtime` | `spec_change_sensor` in `defs/orchestration/maintenance/definitions.py` |
| `alerting.notify_run_failure` | Prefect: [`pipelines/_shared/alerting.py`](../../pipelines/_shared/alerting.py) `notify_flow_failure`; Dagster: log-only `dwh_failure_sensor` |

Extracting these four into the registry is compiler prep: `poll(...)` and `checks:` can only be
validated against names that exist.

## 2. Group-by-group mapping

Every Dagster object below lives in
`experimental/orchestration/dagster_ogip/src/dagster_ogip/defs/orchestration/<group>/definitions.py`.

### `warehouse.yml`

| Fixture object | Dagster implementation |
|---|---|
| job `raw_ingest_job` — `select: raw.rawg__games` | `define_asset_job` over the dlt component asset (`K_RAW_DLT`) |
| jobs `staging_job` · `core_job` · `fs_job` | `define_asset_job` over the dbt component assets (`K_STAGING` · `K_CORE` · `K_FS`) |
| job `dwh_assets_job` — `select: raw.rawg__games+` | `AssetSelection.assets("rawg__games").downstream()` |
| job `dwh_incremental_job` — `task: dbt.build` | `@dg.job` → `dg-tasks.sh build-dwh` |
| job `dwh_full_refresh_job` — `task: dbt.build, args: {full_refresh: true}` | `@dg.job` → `dg-tasks.sh build-dwh-full` |
| automations `daily_dwh_full_refresh` · `hourly_dwh_incremental` · `daily_raw_ingest` | three `ScheduleDefinition`s with the same cron strings |
| automation `raw_landed_runs_dwh` — `asset_materialized(raw.rawg__games)` | `@dg.asset_sensor` `raw_landed_sensor` |
| automation `new_postgres_raw_data` — `poll(sensors.landing_rowcount, every=60s)` | `@dg.sensor` `new_postgres_raw_sensor`, `minimum_interval_seconds=60`, row count as cursor |
| check `market_features_nonempty_and_scored` — `blocking: false` | `@dg.asset_check(blocking=False)` `market_features_check` |

### `ingestion.yml`

| Fixture object | Dagster implementation |
|---|---|
| job `dlt_ingest_job` — `select: raw.rawg__games` | `define_asset_job` over `K_RAW_DLT` |
| job `cdc_asset_job` — `select: cdc.landing` | `define_asset_job` over `K_CDC` (`defs/cdc_ingest/`) |
| job `cdc_job` — `task: cdc.catchup, args: {dry_run: true}` | `@dg.job` → `dg-tasks.sh cdc --dry-run` |
| job `parsing_job` — `task: ingest.parse_to_landing` | `@dg.job` → `dg-tasks.sh parsing` |
| job `metacritic_ingest_job` — `task: ingest.metacritic` | registry task live (`src/ogip/tasks/ingest.py`); no Dagster job wired yet — Prefect reaches it through `ingest.all` when `sources.metacritic.enabled` |
| automation `quarter_hourly_cdc` — `cron("*/15 * * * *")` | `ScheduleDefinition quarter_hourly_cdc` |

### `snapshots.yml`

| Fixture object | Dagster implementation |
|---|---|
| asset `fs.market_snapshot` — `task: snapshot.write, partitions: daily_market` | `@dg.asset market_snapshot`, `DailyPartitionsDefinition(start_date="2026-07-01")` = `daily(start=2026-07-01)` |
| job `market_snapshot_job` — `partitioned: true` | `define_asset_job(..., partitions_def=snapshot_partitions)` |
| automation `daily_market_snapshot` — `partition_ready(market_snapshot_job)` | `build_schedule_from_partitioned_job` |

**Known residual duplication:** the `market_snapshot` asset body inlines the snapshot SQL
instead of calling the registry's `snapshot.write` — the same COPY statement exists twice. The
fixture states the target (`task: snapshot.write`); the asset body is the drift the compiler
eliminates.

### `maintenance.yml`

| Fixture object | Dagster implementation |
|---|---|
| job `update_dbt_job` — `task: dbt.parse` | `@dg.job` → `dg-tasks.sh update-dbt` |
| job `update_dbt_changed_job` — `args: {select: "state:modified+", state: dbt}` | `@dg.job` → `dg-tasks.sh update-dbt-changed` (`state:` = the generated dbt project dir; adapters own the concrete path) |
| job `dbt_project_evaluator_job` — `args: {select: "package:dbt_project_evaluator"}` | `@dg.job` → `dg-tasks.sh dbt-evaluate` |
| automations `daily_dbt_subproject_update` · `weekly_dbt_project_evaluator` | two `ScheduleDefinition`s, same crons |
| automation `spec_change_updates_dbt` — `poll(sensors.spec_sql_mtime, every=30s)` | `@dg.sensor spec_change_sensor`, spec mtime as cursor |

### `integrations.yml`

| Fixture object | Dagster implementation |
|---|---|
| job `prefect_trigger_job` — `task: integrations.trigger_prefect, targets: [dagster]` | `@dg.job` → `dg-tasks.sh prefect`. Dagster-only by construction: Prefect triggering itself is meaningless |

### `monitoring.yml`

| Fixture object | Dagster implementation |
|---|---|
| hook `dwh_run_failure_alert` — `run_failed(scope=location), targets: [dagster]` | `@dg.run_failure_sensor dwh_failure_sensor` (log-only today; the alerting lane's Notifier is the hook point) |

The portable failure path is not this hook but `_defaults.yml`'s
`on_failure: alerting.notify_run_failure` — already real on the Prefect side as
`@flow(on_failure=[notify_flow_failure])`.

## 3. Components — referenced, not described

Per [SPEC.md](SPEC.md) §1, orchestrator Components stay outside portable documents. The fixtures
*reference* the assets these produce (`raw.rawg__games`, `staging.stg_games`, `core.game`,
`fs.market_features`, `cdc.landing`); the components themselves are Dagster-native:

| Component | File | Produces |
|---|---|---|
| `dagster_dbt.DbtProjectComponent` | `defs/dbt_ingest/defs.yaml` (`select: "tag:daily"`) | the dbt asset graph generated from `spec/` |
| `dagster_dlt.DltLoadCollectionComponent` | `defs/dlt_ingest/defs.yaml` | `raw.rawg__games` |
| CDC asset | `defs/cdc_ingest/definitions.py` | `cdc.landing` |

## 4. The Prefect projection

[`make_engine_flow`](../../pipelines/flows/_common.py) is today's hand-written equivalent of the
ordered-flow projection: one flow per engine running the chain
`ingest.all → build_warehouse(engine) → build_ml_outputs → publish_outputs` as `@materialize`
steps. In fixture terms it corresponds to `dwh_assets_job` (`select: raw.rawg__games+`) extended
with the ML/publish tail, which belongs to the production pipeline rather than to the six-group
model.

Two facts the governing design (§7.3) assigns to ODOS are visible here:

- **Asset keys are engine-namespaced URIs** — `file://ogip/{engine}/raw/rawg__games`,
  `duckdb://ogip/{engine}/core.game`. One logical asset therefore has a different Prefect key
  per run profile; the dotted-name → URI mapping (and whether the engine namespace stays in it)
  is an ODOS compiler decision, not a flow-author choice.
- **`on_failure` is already portable** — `@flow(on_failure=[notify_flow_failure])` is exactly
  `_defaults.yml`'s `on_failure: alerting.notify_run_failure` rendered by hand.

## 5. What the compiler still owes ([#37](https://github.com/dataengy/ogip/issues/37))

- The IR + frontend (defaults merge, `select:` expansion against ODTS lineage, registry
  validation, closed-vocabulary enforcement) and the `to_dagster.py` / `to_prefect.py` adapters.
- The **equivalence test** — same ordered registry task names + args in both projections; the
  gate that makes drift a CI failure instead of a code-review hope.
- Registry extraction of the four inline names in §1, plus the `snapshot.write` duplication in
  §2 snapshots.
- The `poll` cursor store for Prefect (Prefect Variables are the candidate) and the asset-key
  mapping decision above.
- Live `spec/orchestration/*.yml` documents replacing both hand-written projections.
