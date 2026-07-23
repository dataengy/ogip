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

Four engine snapshots are **committed** — `dbt/`, `opendbt/`, `sqlmesh_dbt/`, `bruin/`
(reviewable diffs when the spec changes) — and carry repo-relative paths, so run every engine
**from the repo root**. Regenerate them with `just spec-compile` / `uv run python -m
ogip.spec_compile all` (`export UV_PROJECT_ENVIRONMENT=.run/venv` first); a single engine via
`uv run python -m ogip.spec_compile <engine>`. `src/tests/unit/test_engine_projects_cover_spec.py`
is the drift guard — it fails if any committed snapshot is missing a model that `spec/sql`
declares, so a `spec/sql` change that forgets regeneration cannot pass `make check`.

`transform/sqlmesh/models/` is the exception: it is **`.gitignore`d, not committed**. SQLMesh is
the production engine and `pipelines/_shared/steps.py::build_warehouse` recompiles it fresh from
`spec/sql` immediately before every real run, so there is no committed snapshot for it to drift
from — the same test file guards it differently, by exercising the live `compile_to_sqlmesh`
compiler against a temp dir instead of checking a directory in the repo.

**Known gap — SQLMesh audits compile but are not executed by `make check`.** The `checks:` on
every `spec/sql` model project into SQLMesh `audits (...)` clauses (`to_sqlmesh.py`), but
`make check` runs `pytest -m "not integration and not e2e"`, which never plans/applies SQLMesh
against a real warehouse — so those audits are never evaluated by the default gate. Only
`uv run pytest src/tests/e2e/test_all_setups.py::test_base_setup_builds_and_produces_ml -k
sqlmesh` (marked `e2e`, excluded from `make check`) or a live `prefect-sqlmesh` run actually
executes them. A `not_null` regression can — and did — ship past a green `make check`. See
[ADR-0019](../docs/adr/ADR-0019-odts-dq-projection-and-seven-prefect-subprojects.md) and
[ODTS IMPLEMENTATION.md](../spec/ODTS/IMPLEMENTATION.md).

## Why the compiler parses SQL instead of string-matching it

`src/ogip/spec_compile/dialect.py` (SQLGlot) does the work that needs to *understand* the SQL:
rewriting `staging.stg_games` → `{{ ref('stg_games') }}` only where it is a real table
reference (a regex also rewrites it inside string literals), deriving lineage from the SQL to
cross-check the hand-written `depends`, and retargeting a model to another dialect. That last
one makes the portable-SQL policy ([AGENTS.md](../AGENTS.md) hard rule 7; OGAP's own ADR-0016
upstream — not this repo's [ADR-0016](../docs/adr/ADR-0016-odts-authoring-format-spec-sql.md))
executable — the
test suite retargets every spec model to Postgres/ClickHouse/BigQuery on each run.

Engine-specific SQL, when unavoidable, lives in `spec/sql/_ext/<engine>/` — never here.
