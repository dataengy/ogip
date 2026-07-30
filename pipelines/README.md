# `pipelines/`

**Prefect 3** flows and deployments (ADR-0007). Separated, independently
`prefect deploy`-able sub-projects share ONE step library — no per-engine duplication.
The **primary** sub-projects (dbt · bruin, [ADR-0020](../docs/adr/ADR-0020-dbt-bruin-primary-transform-engines.md))
live here; the five comparison sub-projects (`sqlmesh`, `plain_sql`, `opendbt`,
`sqlmesh_dbt`, `dagster`) live under [`experimental/pipelines/`](../experimental/pipelines/)
(re-root #40) with the same shape.

| Subdir | Holds |
|---|---|
| `_shared/` | The one step library: `steps.py` (`ingest_raw`, `build_warehouse`, `build_ml_outputs`, `publish_outputs`, `make_engine_flow`), `alerting.py` (`notify_flow_failure`), `paths.py` (repo-relative constants), `engines.py` (`ENGINE_FLOWS`: transform name → sub-project module, primary or experimental) |
| `dbt/`, `bruin/` | The two primary Prefect sub-projects (A12 run-profile matrix). Each is `{__init__.py, flow.py, prefect.yaml}`: `flow.py` imports `pipelines._shared.steps` and exposes exactly one `flow` object; `prefect.yaml` is that sub-project's own deployment definition, deployable on its own (`prefect deploy` from inside the directory) without pulling in the others |
| `flows/` | `main.py` only — the canonical entry point. Re-exports the **primary** setup (`pipelines.dbt.flow`) as `ingest_transform_publish`, so `make run`, the e2e test, and `src/ogip/tasks/integrations.py` (which shells `python -m pipelines.flows.main`) keep working unchanged |

## How a run profile resolves to a flow

`src/scripts/run-profile.py` reads `config/config.yml → run_profiles[<name>].transform`, looks it
up in `pipelines._shared.engines.ENGINE_FLOWS`, and imports that sub-project's `flow` — nothing
eagerly imports all seven (the `dagster` sub-project's deps are heavier and stay optional until
that profile is actually selected). Experimental profiles print an `[EXPERIMENTAL]` banner.

## Dagster sub-project: Prefect is the OUTER orchestrator

`experimental/pipelines/dagster/flow.py` is the one sub-project that is not a plain SQL runner: Prefect stays
the platform's outer orchestrator, but the **dlt ingestion + dbt transform** combo runs *under*
Dagster (`experimental/orchestration/dagster_ogip`, via `dg launch`) — Dagster owns the narrow,
asset-graph-shaped part it is best at. Prefect wraps that step in a `@materialize` asset, then
runs the ML feature matrix and publish itself, same as every other engine. This is the seam
between the two orchestrators over one shared warehouse.

_Built from Phase 6; M0 wired the minimal end-to-end flow; Part 3.1-3.3 (#37) extracted the shared
step library and separated every engine into its own deployable sub-project._
