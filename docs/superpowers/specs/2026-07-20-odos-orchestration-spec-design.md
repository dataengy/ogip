# ODOS 0.1 — Open Data Orchestration Standard (design)

- **Date:** 2026-07-20
- **Status:** approved → [ADR-0017](../../adr/ADR-0017-odos-normative-profile.md) and
  [`spec/ODOS`](../../../spec/ODOS/README.md)
- **Lane:** `orchestration`
- **Relates to:** [ADR-0005](../../adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md) (`spec/` as SSoT) ·
  [ADR-0007](../../adr/ADR-0007-prefect-orchestration.md) (Prefect, production) ·
  [ADR-0015](../../adr/ADR-0015-dagster-alt-orchestration-dg-components.md) (Dagster via `dg` Components) ·
  [ADR-0016](../../adr/ADR-0016-odts-authoring-format-spec-sql.md) (ODTS, the sibling format)

## 1. Where ODOS sits

The owner's standards taxonomy is three-level:

| | Name | Owns |
|---|---|---|
| **YADPS** | Yet Another Data **Platform** Standard | the umbrella |
| **ODTS** | Open Data **Transformation** Standard | `spec/sql` — *what* is computed |
| **ODOS** | Open Data **Orchestration** Standard | `spec/orchestration` — *when, in what order, and how it survives failure* |

`spec/sql/AGENTS.md` already draws this line from the other side: *"do not treat orchestrators
as compile targets — Prefect and Dagster **consume** compiled projects, they are an orthogonal
axis."* ODOS is that axis. It never describes a transformation; it schedules one.

> **Governing naming decision.** ADR-0016 names the umbrella **YADPS** because `ODPS` collides;
> ODTS and ODOS keep their `Open` names. This document follows that accepted taxonomy.

## 2. Problem

Orchestration in OGIP is currently defined **twice**, in two unrelated dialects:

- `experimental/orchestration/dagster_ogip/jobs/dg-tasks.sh` — a bash dispatch of 9 tasks, wired
  to Dagster ops/jobs/schedules/sensors in `defs/orchestration/<group>/definitions.py`;
- `pipelines/flows/_common.py` + `pipelines/flows/engines/*.py` — Python step functions wrapped
  into Prefect flows and assets.

**They have already drifted.** The same logical step — "ensure raw data exists" — is:

```bash
# dg-tasks.sh:43 — Dagster lane
ensure_raw() {
  if ! ls "$REPO"/.run/data/raw/rawg__games/*.parquet >/dev/null 2>&1; then
    uv run dg launch --assets 'key:"raw/rawg__games"'      # via the orchestrator
  fi
}
```
```python
# pipelines/flows/_common.py:39 — Prefect lane
def ingest_raw() -> str:
    return RawgGames(settings).run(settings.platform.data_dir)   # straight to dlt
```

Conditional vs unconditional; through the orchestrator vs around it. Nothing detects this. It is
the orchestration-layer analogue of ODTS's `sk = md5(id)` hazard: valid, runnable, silently
different.

ODOS exists to make that state unrepresentable.

## 3. Non-goals

ODOS is **internal to OGIP**, judged against portability across **two** targets (Dagster 1.13.x,
Prefect ≥3.4), not against an imagined industry. Concretely, do not:

- describe transformations — that is ODTS;
- add a third orchestrator to the target set before one is actually adopted;
- model instance/deployment config (`dagster.yaml`, storage, run coordinator) — that is
  `config/config.yml` per hard rule 3, and duplicating it would create a second SSoT;
- expose an open key set (see §4.9);
- version blocks independently — one ODOS version per file, whole-file (same rule as ODTS).

## 4. The format

### 4.1 Layout

```
spec/orchestration/
  _defaults.yml       # shared partitions, owner, retry/concurrency defaults, registry root
  ingestion.yml       warehouse.yml      snapshots.yml
  maintenance.yml     integrations.yml   monitoring.yml
  _ext/dagster/       # irreducibles: dg Components (defs.yaml)
```

One file per **group**. Groups match the existing `defs/orchestration/<group>/` split, so the
diff between spec and reality stays readable during migration.

### 4.2 File skeleton

```yaml
odos: 0.1
group: warehouse
doc: Building the DWH from raw to the FS layer.

assets:       {}    # orchestrator-native assets only (§4.4)
jobs:         {}    # units of execution (§4.3)
automations:  {}    # what starts a job (§4.5)
checks:       {}    # asset-level correctness gates (§4.6)
hooks:        {}    # location-scoped reactions (§4.6a) — rarely portable
```

Every section is optional. `odos` and `group` are required.

Three keys are accepted on any object in any section: `doc:` (free text, rendered into the
target's `description`), `tags:` (string map, passed through to both targets' tag facilities), and
`targets:` (list, restricting which orchestrators the object compiles into — see §7).

### 4.3 Jobs

Two forms, and only two:

```yaml
jobs:
  fs_job:              { select: fs.market_features }          # asset job
  dwh_assets_job:      { select: raw.rawg__games+ }            # + = downstream closure
  dwh_incremental_job: { task: dbt.build }                     # task job
  dwh_full_refresh_job:
    task: dbt.build
    args: { full_refresh: true }
    tags: { pipeline: dwh, mode: full-refresh }
```

**`select:` grammar** — a deliberately small subset, shared with dbt/Dagster convention:
`name` · `name+` (downstream closure) · `+name` (upstream closure) · `tag:<t>` · a list of these.
Nothing else. No arbitrary selection algebra until a second model needs it.

`partitioned: true` marks a job that runs one partition per launch; it is valid only when every
selected asset shares a `partitions:` definition, and the compiler checks that.

**`select:` is resolvable only because ODTS publishes lineage.** The compiler expands a selection
against the asset graph derived from ODTS `depends` + `dialect.table_refs()`, plus assets declared
in §4.4. This is the concrete reason YADPS is one family rather than two unrelated formats:
Dagster resolves selections natively, Prefect has no selection engine at all, and the Prefect
adapter can only emit an ordered flow because the graph is already known statically.

### 4.4 Assets

Declared **only** for assets that exist in neither ODTS nor a component — today exactly one:

```yaml
assets:
  fs.market_snapshot:
    task: snapshot.write
    partitions: daily_market        # named in _defaults.yml
    kinds: [duckdb, parquet]
    group_name: marts
```

Asset keys are ODTS dotted names (`core.game`), never orchestrator-native key tuples. The
Dagster-side collision between the dbt raw model and the dlt asset (ADR-0015, "Consequences") is
an adapter concern and does not surface in the spec.

### 4.5 Automations

One key, `on:`, with a closed set of four forms:

```yaml
automations:
  hourly_dwh_incremental: { on: cron("0 * * * *"),                        run: dwh_incremental_job }
  raw_landed_runs_dwh:    { on: asset_materialized(raw.rawg__games),      run: dwh_assets_job }
  new_postgres_raw_data:  { on: poll(sensors.landing_rowcount, every=60s), run: dwh_incremental_job }
  daily_market_snapshot:  { on: partition_ready(market_snapshot_job) }
```

`poll(...)` names a registry callable returning a cursor token or `None` — the portable core of a
polling sensor, with the cursor-comparison and skip-reason boilerplate generated per target.
`partition_ready` needs no `run:`; the job is its argument.

### 4.6 Checks

```yaml
checks:
  market_features_nonempty_and_scored:
    asset: fs.market_features
    task: checks.market_features_nonempty
    blocking: false
```

Correctness gates on an asset. Consistent with ODTS's split: statistical monitoring (freshness,
volume, drift) is observability and belongs to `dq/` and the obs lane, not here.

### 4.6a Hooks

Reactions scoped to the whole code location rather than to one job:

```yaml
hooks:
  dwh_run_failure_alert:
    on: run_failed(scope=location)
    task: alerting.notify_run_failure
    targets: [dagster]
```

Deliberately marginal. The portable way to react to failure is job-level `on_failure:` (§4.7);
`hooks:` exists only for what genuinely has no per-job equivalent, and every entry is expected to
carry a `targets:` restriction. If §13.4 resolves against it, this section disappears in 0.2.

### 4.7 Resilience

The most portable part of the format, and the part a first draft is most likely to omit. Both
targets support all three natively:

| | Dagster 1.13 | Prefect ≥3.4 |
|---|---|---|
| retry | `RetryPolicy(max_retries, delay, backoff)` | `@task(retries=, retry_delay_seconds=)` |
| concurrency | run queue + concurrency keys | concurrency limits |
| on-failure | `@failure_hook` | `on_failure=[...]` (already used in `_common.py`) |

```yaml
jobs:
  dwh_incremental_job:
    task: dbt.build
    retry:       { max_attempts: 3, type: exponential, interval: PT1M }
    concurrency: { limit: 1, behavior: cancel }        # queue | cancel | fail
    on_failure:  alerting.notify_run_failure
```

Durations are ISO-8601 (`PT1M`) — unambiguous, borrowed from Kestra. Defaults live in
`_defaults.yml`, so a typical job carries none of these keys. Per ODTS's "infer before you
require" gate, a directive that can be defaulted should not be authored.

### 4.8 Defaults

```yaml
# _defaults.yml
odos: 0.1
owner: data-eng@ogip
registry: ogip.tasks

partitions:
  daily_market: daily(start=2026-07-01)

defaults:
  retry:       { max_attempts: 2, type: constant, interval: PT30S }
  concurrency: { limit: 1, behavior: queue }
  on_failure:  alerting.notify_run_failure
```

Merged into every job in every group file; a job-level key overrides. Same shape as dag-factory's
`default:` block.

### 4.9 The closed-vocabulary rule

**Any key ODOS does not define is a compile error.** No pass-through to the orchestrator's
constructor.

This is the single largest divergence from dag-factory, which consumes only four task keys
(`operator`, `dependencies`, `task_group_name`, `parent_group_name`) and forwards everything else
verbatim to the Airflow operator. With one target that is convenient; with two unequal targets it
is a silent-loss machine — a key Dagster understands would simply vanish from the Prefect
projection, and nothing would say so. Open key sets and portability are incompatible.

## 5. The task registry

Every `task:` names an entry in a **closed registry** of plain, typed Python functions under
`src/ogip/tasks/`. The name is a registry key, not an import path:

```python
@odos_task("dbt.build")
def dbt_build(*, full_refresh: bool = False, select: str | None = None,
              state: str | None = None) -> None: ...
```

Named registration over `module:function` paths, following dagster-odp's `@odp_task("...")` +
`task_type:` pattern, for three reasons that matter specifically to AI-driven authoring:

1. the compiler validates the name against the registry and **fails on a typo** — an import path
   would produce a dangling reference that only surfaces at runtime;
2. an agent selects from an enumerable vocabulary instead of inventing a path;
3. the spec survives module reorganisation.

Unlike dagster-odp, no `BaseTask` subclass — a decorated function is enough. Inheritance for the
sake of registration is ceremony.

**The registry is small.** Six of the nine `dg-tasks.sh` tasks are one operation with different
flags:

```
build-dwh · build-dwh-full · dbt-evaluate · update-dbt-changed  →  dbt.build(...)
update-dbt                                                       →  dbt.parse()
dbt-deps                                                         →  dbt.deps()
```

Whole-project vocabulary, projected: `dbt.build` · `dbt.parse` · `dbt.deps` · `ingest.rawg` ·
`cdc.catchup` · `snapshot.write` · `integrations.trigger_prefect` — plus sensor and check
callables. The differences move into `args:`, where they are visible to both targets.

**Regeneration is implicit.** Every `dbt.*` task regenerates the dbt project from `spec/` before
acting (`compile_to_dbt`), and resolves packages idempotently — exactly what `compile_dbt` and
`ensure_deps` do in the bash today. Since `spec/` is the SSoT (ADR-0005) and the generated project
is never hand-edited, a spec that had to *ask* for regeneration would be authoring a fact the
system already knows. Per ODTS's "infer before you require": not a directive.

### 5.1 Why no `sh(...)` escape hatch

A transitional `run: sh(build-dwh)` form would let the Dagster lane keep shelling to bash while
Prefect runs Python. The format would then guarantee nothing: one spec, two behaviours, divergence
discovered in production rather than in the compiler. §2 shows this is not hypothetical — it is
the state of the repo today.

**Honest cost.** Only one of the nine bash tasks has a full Python equivalent today
(`compile_dbt`, which already heredocs into `ogip.spec_compile.to_dbt.compile_to_dbt`); two are
partial (`transform/engines.py:_run_dbt`, with a different dependency resolution —
`uv run --group engines` vs the project venv, and no `--full-refresh`); four dbt-maintenance tasks
have none. This is writing three or four thin `subprocess` wrappers, plus one real decision: which
`ensure_raw` semantics — conditional or unconditional — is correct. A day, not an hour.

Justification under AGENTS.md rule 2 ("no abstraction without two call sites"): two orchestrators
are two call sites.

## 6. The model: `experimental/orchestration/dagster_ogip` in ODOS

The whole code location, six groups. This doubles as the format's acceptance test — anything not
expressible here is a gap in the format, not in the project.

### `warehouse.yml`

```yaml
odos: 0.1
group: warehouse
doc: Building the DWH from raw to the FS layer.

jobs:
  raw_ingest_job:      { select: raw.rawg__games,  doc: "Layer 0 — RAWG → raw Parquet via dlt." }
  staging_job:         { select: staging.stg_games }
  core_job:            { select: core.game }
  fs_job:              { select: fs.market_features }
  dwh_assets_job:      { select: raw.rawg__games+, doc: "Whole DWH: raw→stg→core→fs." }
  dwh_incremental_job: { task: dbt.build, tags: { pipeline: dwh, mode: incremental } }
  dwh_full_refresh_job:
    task: dbt.build
    args: { full_refresh: true }
    tags: { pipeline: dwh, mode: full-refresh }

automations:
  daily_dwh_full_refresh: { on: cron("0 3 * * *"),  run: dwh_full_refresh_job }
  hourly_dwh_incremental: { on: cron("0 * * * *"),  run: dwh_incremental_job }
  daily_raw_ingest:       { on: cron("30 1 * * *"), run: raw_ingest_job }
  raw_landed_runs_dwh:    { on: asset_materialized(raw.rawg__games), run: dwh_assets_job }
  new_postgres_raw_data:
    on:  poll(sensors.landing_rowcount, every=60s)
    run: dwh_incremental_job

checks:
  market_features_nonempty_and_scored:
    asset: fs.market_features
    task: checks.market_features_nonempty
    blocking: false
```

### `ingestion.yml`

```yaml
odos: 0.1
group: ingestion
jobs:
  dlt_ingest_job: { select: raw.rawg__games }
  cdc_asset_job:  { select: cdc.landing }
  cdc_job:        { task: cdc.catchup, args: { dry_run: true }, tags: { ingestion: cdc } }
  parsing_job:    { task: ingest.parse_to_landing, tags: { ingestion: scraping } }
automations:
  quarter_hourly_cdc: { on: cron("*/15 * * * *"), run: cdc_job }
```

### `snapshots.yml`

```yaml
odos: 0.1
group: snapshots
assets:
  fs.market_snapshot:
    task: snapshot.write
    partitions: daily_market
    kinds: [duckdb, parquet]
    group_name: marts
jobs:
  market_snapshot_job: { select: fs.market_snapshot, partitioned: true }
automations:
  daily_market_snapshot: { on: partition_ready(market_snapshot_job) }
```

### `maintenance.yml`

```yaml
odos: 0.1
group: maintenance
jobs:
  update_dbt_job:            { task: dbt.parse, tags: { maintenance: dbt } }
  update_dbt_changed_job:
    task: dbt.build
    args: { select: "state:modified+", state: dbt }
    tags: { maintenance: dbt }
  dbt_project_evaluator_job:
    task: dbt.build
    args: { select: "package:dbt_project_evaluator" }
    tags: { maintenance: dbt, package: dbt_project_evaluator }
automations:
  daily_dbt_subproject_update:  { on: cron("0 2 * * *"), run: update_dbt_job }
  weekly_dbt_project_evaluator: { on: cron("0 4 * * 1"), run: dbt_project_evaluator_job }
  spec_change_updates_dbt:
    on:  poll(sensors.spec_sql_mtime, every=30s)
    run: update_dbt_changed_job
```

### `integrations.yml`

```yaml
odos: 0.1
group: integrations
jobs:
  prefect_trigger_job:
    task: integrations.trigger_prefect
    tags: { orchestration: prefect }
    targets: [dagster]        # Prefect triggering itself is meaningless
```

### `monitoring.yml`

```yaml
odos: 0.1
group: monitoring
hooks:
  dwh_run_failure_alert:
    on: run_failed(scope=location)
    task: alerting.notify_run_failure
    targets: [dagster]        # no location-scoped equivalent in Prefect
```

`monitoring.yml` is the one group ODOS does **not** fully own. The portable form is job-level
`on_failure:` (§4.7), defaulted in `_defaults.yml`; the location-scoped Dagster sensor stays an
explicitly target-restricted extra rather than a fiction of portability.

### Components

`dg` Components (`dagster_dbt.DbtProjectComponent`, `dagster_dlt.DltLoadCollectionComponent`) stay
in `_ext/dagster/` verbatim. They have no Prefect analogue whatsoever, and abstracting them would
be exactly the vendor leak ODTS forbids. The spec **references** the assets they produce; it does
not describe them.

## 7. Capability matrix and failure policy

| ODOS construct | Dagster 1.13 | Prefect ≥3.4 | Projection |
|---|---|---|---|
| `select:` job | `define_asset_job(selection=)` | none | ordered flow, derived from the ODTS graph |
| `task:` job | `@job` over `@op` | `@flow` over `@task` | direct |
| `assets:` | `@asset` | `@materialize` | direct |
| `on: cron` | `ScheduleDefinition` | deployment schedule | direct |
| `on: asset_materialized` | `@asset_sensor` | Automation + `EventTrigger` (Reactive) | direct — §7.1 |
| `on: poll` | `@sensor` + cursor | none (no sensor daemon) | scheduled deployment + external cursor — §7.2 |
| `on: partition_ready` | `build_schedule_from_partitioned_job` | none | cron + partition arg |
| `checks:` | `@asset_check` | none | validation gate task after the asset |
| `hooks: run_failed` | `@run_failure_sensor` | none | target-restricted |
| `retry`/`concurrency`/`on_failure` | native | native | direct |

**Policy: the compiler fails loudly.** An object that cannot be projected into a requested target
is a compile error unless it carries an explicit `targets:` restriction. Silently dropping it is
forbidden — that is how a spec starts lying about what runs.

### 7.1 Verified: Prefect expresses `asset_materialized` natively

Established by **running** Prefect 3.7.8 (installed in `.run/venv`), not by reading docs:

- `@materialize` emits `prefect.asset.materialization.succeeded` / `.failed`, with
  `prefect.resource.id` set to the asset key, plus `prefect.asset.referenced` for each upstream.
  Observed for a two-step `@materialize` flow.
- `EventTrigger(expect={"prefect.asset.materialization.succeeded"}, match={"prefect.resource.id":
  <key>}, posture=Reactive)` + a `RunDeployment` action validates as an `AutomationCore`.
- `Posture.Proactive` with `within=` gives absence/freshness triggers; `MetricTrigger` exists too.
  Both are OSS, no Cloud requirement; an ephemeral API server starts on demand.

So `on: asset_materialized` is a **direct projection on both targets** — this is not a gap, and
the earlier assumption that it might be one was wrong. Two caveats found in the same pass, both
from `prefect/context.py:emit_events`: a `Cached` state emits nothing, and a task with no
downstream asset emits no materialization event. Any ODOS automation whose upstream job can be
cached needs that stated, or it will look like a missed trigger.

### 7.2 `on: poll` is the one real asymmetry

Prefect has no cursor-holding sensor daemon. The projection is a scheduled deployment running the
registry callable at `every=`, comparing against a cursor kept outside the flow. Dagster stores
the cursor for you; Prefect does not, so **the cursor store is an ODOS decision, not an adapter
detail** — otherwise the two projections diverge exactly like §2. Prefect Variables are the
obvious candidate; deciding this is part of the implementation task.

### 7.3 Asset-key mapping is ODOS's, not the flow author's

Prefect asset keys are URIs; Dagster's are key tuples. Today `make_engine_flow` builds Prefect
URIs **namespaced by engine** — `file://ogip/{engine}/raw/rawg__games` — so one logical asset has
a different Prefect key per run profile. An `EventTrigger` matches on the concrete URI, so a
naive port would produce automations that fire for one profile and silently never for another.

ODOS therefore owns the dotted-name → URI/key-tuple mapping convention, and the engine namespace
becomes part of that mapping rather than a formatting choice inside a flow module.

## 8. Compiler architecture

Front-end parses ODOS YAML into a typed IR (Pydantic v2, per hard rule 4), resolves `_defaults`,
expands `select:` against the ODTS-derived asset graph, and validates every `task:`/`poll:` name
against the registry. Adapters render the IR:

```
spec/orchestration/*.yml ──▶ ODOS IR ──┬──▶ to_dagster.py ──▶ defs/orchestration/<group>/definitions.py
                                       └──▶ to_prefect.py ──▶ pipelines/flows/<group>.py
             ▲
    spec/sql (ODTS) ── asset graph
```

Lives beside its sibling as `src/ogip/spec_compile/` → `to_dagster.py`, `to_prefect.py`. Gates
extend the existing ones: `just spec-compile all`, `just spec-verify`, `make check`.

**Where AI operates** (the hybrid boundary): the compiler deterministically renders all structure
— jobs, selections, schedules, sensor scaffolding, partitions, retry/concurrency wiring,
`Definitions` assembly. An agent authors (a) the ODOS YAML and (b) task-registry function bodies,
both of which are ordinary reviewable artifacts. No generation step sits between the spec and the
running code.

## 9. Testing

- **Round-trip:** every group file compiles to both targets; `spec-verify` asserts committed
  output matches a fresh compile.
- **Load:** `dg check defs` for Dagster; import-and-inspect for Prefect flows.
- **Equivalence** — the one that earns the format: for a job present in both projections, assert
  the same ordered sequence of registry task names with the same args. This is what would have
  caught the `ensure_raw` drift in §2, and it is the ODOS counterpart of ODTS's macro conformance
  tests.
- **Negative:** an unknown key, an unknown `task:` name, and an unprojectable object without
  `targets:` each fail compilation.

## 10. Versioning

One `odos:` version per file, whole-file, mirroring ODTS. `0.1` is the scope described here.
Deferred, explicitly not rejected: task-level graphs inside a job (only if a job ever needs more
than one task), `inputs:`/parameterised runs, backfill policy declarations.

## 11. Alternatives rejected

- **Task-graph-first (Kestra / dag-factory literal)** — `jobs.tasks[].dependencies[]` with assets
  secondary. Natural for Prefect, wrong for Dagster: the real project is `define_asset_job(
  selection=...)` throughout, so the format would force authors to spell out a graph Dagster
  derives, and the reverse projection into selections would be lossy. It would describe something
  other than what exists.
- **Intent-only + full AI projection** — spec states intent, an agent generates both targets,
  golden tests verify. Maximum flexibility, but token-expensive and irreproducible; rejected
  against the brief's explicit "maximise the deterministic surface".
- **Open key pass-through (dag-factory)** — see §4.9.
- **Modelling instance/deploy config** — see §3.

## 12. Consequences

- Orchestration gains a single source of truth; the §2 drift becomes a test failure.
- `dg-tasks.sh` and `pipelines/flows/_common.py` collapse into `src/ogip/tasks/` — the registry
  becomes typed, pyright-strict, and unit-testable, which bash never was.
- A third SSoT consumer joins `to_sqlmesh.py`/`to_dbt.py`; ODTS and ODOS must stay in step, and
  the asset-graph interface between them becomes load-bearing.
- Cost, honestly: three or four `subprocess` wrappers, the `ensure_raw` semantics decision, the
  IR + two adapters, and the equivalence-test harness.

## 13. Open questions

1. ~~**Prefect ≥3.4 event/automation surface**~~ — **resolved by running 3.7.8**, see §7.1–7.3.
   `asset_materialized` projects directly; `poll` does not and needs a cursor-store decision;
   asset-key mapping turns out to belong to ODOS. Two new sub-questions replace it: which cursor
   store (Prefect Variables?), and how the engine namespace enters the key mapping.
2. **`ensure_raw` semantics** — conditional (skip when parquet present) or unconditional? The
   registry must pick one, and it is a behaviour change for whichever lane loses.
3. **Flat `automations:` vs nesting triggers under jobs** (dagster-odp's `jobs[].triggers[]`).
   Flat keeps `raw_landed_runs_dwh` attached to the asset it actually watches; nesting puts a
   schedule next to what it starts. Currently flat; genuinely arguable.
4. **`monitoring` group** — whether it survives at all once `on_failure:` is defaulted, or reduces
   to one Dagster-only extra.
