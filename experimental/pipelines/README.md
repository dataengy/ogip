# `experimental/pipelines/` — comparison / R&D transform setups

Separately-deployable Prefect sub-projects for the transform engines that are **not** the two
primary comparison candidates. Off the default `make`/pipeline path (re-root, ADR-0020, #40).

| Sub-project | Setup | Status |
|---|---|---|
| `sqlmesh/` | Prefect + SQLMesh (was the production default) | experimental |
| `plain_sql/` | Prefect + plain-SQL runner | experimental |
| `opendbt/` | Prefect + OpenDBT (dbt-core extended) | experimental |
| `sqlmesh_dbt/` | Prefect + SQLMesh-over-dbt | experimental (heavy-e2e broken — #42) |
| `dagster/` | Dagster (dlt+dbt) wrapped in Prefect | experimental |

Each is `{__init__.py, flow.py, prefect.yaml}` importing the shared step library from
`pipelines._shared`; identical in shape to the primary sub-projects under `pipelines/`, only
the location differs. The flow registry `pipelines._shared.engines.ENGINE_FLOWS` maps each to
`experimental.pipelines.<engine>.flow`.

The two **primary** candidates — **dbt** and **bruin** — live under `pipelines/` and are the
ones `make check` / the default e2e exercise. These comparison engines run only behind
`OGIP_E2E_ALL_ENGINES=1`.
