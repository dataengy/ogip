# Task — Transform setups as generators from `spec/sql` (A12 comparison engines)

**Status:** 🟢 shipped — every `transform/` setup is generated from the one `spec/sql`; a
SQLGlot AST layer replaces the text-substitution ref-rewrite; cross-engine parity is a gate.

## What

Fill `transform/` per its README and the run-profile matrix (AGENTS.md → "Run & orchestration
profiles"): every non-default transform setup is a **generator from `spec/sql`** (Bruin asset
format, the SSoT — [ADR-0005](../../docs/adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md)), never
hand-authored. Production stays **SQLMesh** ([ADR-0004](../../docs/adr/ADR-0004-sqlmesh-default-transform-engine.md)).

## Delivered

- **`src/ogip/spec_compile/dialect.py`** — SQLGlot layer. Parses spec SQL to an AST for:
  ref-rewriting (only real table references, never inside string literals/comments — the
  regression a regex causes), lineage derived from the SQL (cross-checked against hand-written
  `depends`), and dialect retargeting (`transpile`) — the portable-SQL policy made executable.
- **Generators** (all under `src/ogip/spec_compile/`): `to_sqlmesh` (existing, production) ·
  `to_dbt` (existing; ref-rewrite now AST-based) · `to_sqlmesh_dbt` (**new** — dbt project +
  SQLMesh dbt-loader `config.py`, out-of-warehouse state) · `to_bruin` (**new** — verbatim
  pass-through, since spec *is* Bruin, + project shell).
- **`__main__.py`** — `just spec-compile [engine]` regenerates `transform/{sqlmesh,dbt,sqlmesh_dbt,bruin}/`.
- **`transform/runner.py`** — plain-SQL runner (`prefect-sql`): topo-sort `depends`,
  `create or replace` on DuckDB, no framework.
- **`transform/engines.py`** — launcher: regenerate the engine's project from `spec/`, then run it.
- **OpenDBT** (`prefect-opendbt`) — the same generated dbt project run through **OpenDBT**
  (dbt-core extended: local-python/DLT models, cross-project mesh refs, custom adapters). Its
  own `opendbt` dep group (declared conflicting with `engines`): OpenDBT 0.14 pins dbt <1.10
  and needs sqlglot <30, so it resolves separately. Generated `with_packages=False` — the hub
  versions we track refuse to install under dbt 1.9. Verified: parity OK vs plain-SQL.
- **`src/scripts/run-profile.py`** — resolves `config/config.yml → run_profiles` and drives the
  flow with the profile's engine; the Dagster profile is pointed to its own project.
- **`pipelines/flows/main.py`** — `transform_engine` param threads the profile's engine through
  the flow; the default path never leaves SQLMesh.
- **`src/scripts/spec-compile-verify.py`** (`just spec-verify`) — **cross-engine parity gate**:
  every generated engine builds the SAME `fs.market_features` from one spec, diffed against the
  plain-SQL reference. Verified: plain_sql / dbt / bruin all byte-identical (5/5 rows).

## Verified

`make check` green (ruff, pyright strict 0, pytest). Each engine run end-to-end against the real
RAWG raw fixture: plain_sql, dbt (`PASS=83`), bruin (`4 succeeded, 9 quality checks`),
SQLMesh-over-dbt (plan applied, virtual layer updated). `test_spec_compile.py` pins the
contracts incl. retargeting every model to Postgres/ClickHouse/BigQuery.

## Note vs OGAP

OGAP (`../Hushcrasher/`) hand-maintains `dwh/engines/*` with a portable-SQL **macro** discipline
(`ogap_hash_key()`, `ogap_config()`) — no generator. OGIP **generates** what OGAP hand-wrote;
the macro-portability intent is preserved by the transpile tests.
