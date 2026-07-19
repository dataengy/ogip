# `transform/`

Every transform setup here is **generated from `spec/sql`** (Bruin asset format, the SSoT —
[ADR-0005](../docs/adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md)); none is hand-authored.
Regenerate all of them with `just spec-compile` (one engine: `just spec-compile dbt`).

**Production is SQLMesh on DuckDB, sequenced by Prefect** ([ADR-0004](../docs/adr/ADR-0004-sqlmesh-default-transform-engine.md), D5).
The rest exist so `docs/comparisons/*` measures real runs. Builds `staging → core → star / am → marts → fs`.

| Path | Profile (`just run-profile …`) | What it is |
|---|---|---|
| `sqlmesh/` | `prefect-sqlmesh` **(default, production)** | native SQLMesh models |
| `runner.py` | `prefect-sql` | plain-SQL runner — no framework: topo-sort `depends`, `create or replace` on DuckDB |
| `dbt/` | `prefect-dbt`, `prefect-dagster-dlt-dbt` | generated dbt project (+ dbt-hub packages, `schema.yml` tests from Bruin checks) |
| `opendbt/` | `prefect-opendbt` | same models via **OpenDBT** (dbt-core extended: python/dlt models, mesh refs, custom adapters) — own dep group, pins dbt <1.10 |
| `sqlmesh_dbt/` | `prefect-sqlmesh-over-dbt` | the dbt project + `config.py` so SQLMesh plans/applies it natively |
| `bruin/` | `prefect-bruin` | pass-through — `spec/` *is* Bruin, so assets are copied verbatim + a project shell |
| `engines.py` | — | launcher: regenerates the engine's project from `spec/`, then runs it |

Generated projects are **committed** (reviewable diffs when the spec changes) and carry
repo-relative paths, so run every engine **from the repo root**.

## Why the compiler parses SQL instead of string-matching it

`src/ogip/spec_compile/dialect.py` (SQLGlot) does the work that needs to *understand* the SQL:
rewriting `staging.stg_games` → `{{ ref('stg_games') }}` only where it is a real table
reference (a regex also rewrites it inside string literals), deriving lineage from the SQL to
cross-check the hand-written `depends`, and retargeting a model to another dialect. That last
one makes the portable-SQL policy ([ADR-0016 in OGAP terms](../docs/adr/)) executable — the
test suite retargets every spec model to Postgres/ClickHouse/BigQuery on each run.

Engine-specific SQL, when unavoidable, lives in `spec/sql/_ext/<engine>/` — never here.
