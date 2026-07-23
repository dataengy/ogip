# `pipelines/`

**Prefect 3** flows and deployments (ADR-0007). Seven separated, independently
`prefect deploy`-able sub-projects share ONE step library — no per-engine duplication.

| Subdir | Holds |
|---|---|
| `_shared/` | The one step library: `steps.py` (`ingest_raw`, `build_warehouse`, `build_ml_outputs`, `publish_outputs`, `make_engine_flow`), `alerting.py` (`notify_flow_failure`), `paths.py` (repo-relative constants), `engines.py` (`ENGINE_FLOWS`: transform name → sub-project module) |
| `sqlmesh/`, `plain_sql/`, `dbt/`, `opendbt/`, `sqlmesh_dbt/`, `bruin/`, `dagster/` | One Prefect sub-project per transform engine (A12 run-profile matrix). Each is `{__init__.py, flow.py, prefect.yaml}`: `flow.py` imports `pipelines._shared.steps` and exposes exactly one `flow` object; `prefect.yaml` is that sub-project's own deployment definition, deployable on its own (`prefect deploy` from inside the directory) without pulling in the other six |
| `flows/` | `main.py` only — the canonical entry point. Re-exports the **production** setup (`pipelines.sqlmesh.flow`) as `ingest_transform_publish`, so `just run-profile prefect-sqlmesh`, the e2e test, and `src/ogip/tasks/integrations.py` (which shells `python -m pipelines.flows.main`) keep working unchanged |

## How a run profile resolves to a flow

`src/scripts/run-profile.py` reads `config/config.yml → run_profiles[<name>].transform`, looks it
up in `pipelines._shared.engines.ENGINE_FLOWS`, and imports that sub-project's `flow` — nothing
eagerly imports all seven (the `dagster` sub-project's deps are heavier and stay optional until
that profile is actually selected).

## Dagster sub-project: Prefect is the OUTER orchestrator

`pipelines/dagster/flow.py` is the one sub-project that is not a plain SQL runner: Prefect stays
the platform's outer orchestrator, but the **dlt ingestion + dbt transform** combo runs *under*
Dagster (`experimental/orchestration/dagster_ogip`, via `dg launch`) — Dagster owns the narrow,
asset-graph-shaped part it is best at. Prefect wraps that step in a `@materialize` asset, then
runs the ML feature matrix and publish itself, same as every other engine. This is the seam
between the two orchestrators over one shared warehouse.

_Built from Phase 6; M0 wired the minimal end-to-end flow; Part 3.1-3.3 (#37) extracted the shared
step library and separated every engine into its own deployable sub-project._
