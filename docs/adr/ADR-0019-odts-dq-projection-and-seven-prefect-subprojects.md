# ADR-0019 — ODTS DQ projection into SQLMesh audits + seven separated Prefect sub-projects

- **Status:** Accepted
- **Date:** 2026-07-23
- **Relates to:** [ADR-0004](ADR-0004-sqlmesh-default-transform-engine.md) ·
  [ADR-0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md) ·
  [ADR-0007](ADR-0007-prefect-orchestration.md) ·
  [ADR-0016](ADR-0016-odts-authoring-format-spec-sql.md) ·
  [ADR-0017](ADR-0017-odos-normative-profile.md) ·
  [ADR-0018](ADR-0018-odts-normative-profile.md) ·
  [transform-expansion plan](../superpowers/plans/2026-07-23-transform-expansion-and-six-prefect-subprojects.md)

## Context

Two independent drifts existed on the production path, both closed in the same body of work
(issue #37):

**DQ was authored but not projected.** `spec/sql` `columns[].checks:` is the ODTS §5-6 DQ
vocabulary (`not_null`, `unique`, `non_negative`, `between`, `accepted_values`, plus a
composite top-level `unique`), and `spec/ODTS/IMPLEMENTATION.md` already documented — ahead of
the code — that this projects into "dbt `schema.yml` tests, Bruin checks, SQLMesh audits". The
dbt and Bruin adapters honored it; `to_sqlmesh._model_text` did not: it emitted `MODEL(name,
kind)` and the SQL body only, silently discarding every `columns.checks` entry. SQLMesh is the
production engine (ADR-0004), so the constraint every other adapter enforced was, on the path
that actually runs in production, decorative documentation with no runtime effect. Four of five
raw sources also dead-ended in staging — core/fs consumed only the rawg spine — so there was
comparatively little DQ surface to project in the first place.

**Orchestration was six modules sharing one file, not six deployables.** `pipelines/flows/`
held `engines/prefect_{sqlmesh,dbt,bruin,dagster,opendbt,sqlmesh_dbt}.py`, each a one-line
wrapper over `make_engine_flow` in a shared `pipelines/flows/_common.py`, with no
`prefect.yaml` and no per-setup `deployments/`. Nothing could `prefect deploy` one engine
without importing the whole `pipelines.flows` package, and the plain-SQL profile
(`prefect-sql`) had no sub-project at all — six named setups covering seven run profiles.

## Decision

**DQ:** `to_sqlmesh.py` now renders every `@bruin` check into the `MODEL(...)` block's
`audits (...)` clause (`not_null → not_null(columns := (c))`, `unique → unique_values(columns
:= (c))`, `non_negative → accepted_range(min_v := 0)`, `between(a,b) → accepted_range(min_v :=
a, max_v := b)`, `accepted_values(...) → accepted_values(is_in := (...))`, top-level composite
`unique(columns: [...]) → unique_combination_of_columns(...)`). The mapping is total and
fail-loud: a check name outside this vocabulary raises `SqlSpecError` at compile time — ODTS
SPEC.md §5's "attributes outside the check vocabulary MUST fail compilation" — never a silent
drop. Checks were then authored comprehensively across raw/staging/core/fs (70 audits today),
riding on Part 1's lineage work (a `staging.stg_game_match` title-normalization bridge plus
`core.{critic_reception,console_pricing,traction}`, so all five sources now reach
`fs.market_features`).

**Checks ≠ monitors (ODTS §6).** Row-count floors and freshness windows are not correctness
constraints and were deliberately kept off `columns[].checks:`. They are declared as data in
[`spec/dq/policy.yml`](../../spec/dq/policy.yml) and loaded + reported (count, print a summary,
exit 0) by [`dq/run.py`](../../dq/run.py). This is a load-and-report runner, not an executor —
it does not query the warehouse or evaluate a threshold. The executor (query DuckDB, evaluate
`min_rows`/`max_age_hours`, record to `platform_meta.dq_results`, ADR-0008 severity model:
`error` blocks, `warn` records) is out of scope here and arrives in Phase 4.

**Orchestration:** the shared step library moved once, to `pipelines/_shared/` (`steps.py` —
`ingest_raw`, `build_warehouse`, `build_ml_outputs`, `publish_outputs`, `make_engine_flow`;
`alerting.py` — `notify_flow_failure`; `paths.py` — repo-relative constants; `engines.py` —
`ENGINE_FLOWS`, the transform-name → sub-project-module map). Every run profile became its own
directory, `pipelines/<engine>/{__init__.py, flow.py, prefect.yaml}`, separately
`prefect deploy`-able without pulling in the other six: `sqlmesh` (production default),
`plain_sql`, `dbt`, `opendbt`, `sqlmesh_dbt`, `bruin`, `dagster` — **seven**, not six, once
`plain_sql` got its own sub-project alongside the other five SQL engines plus `dagster`.
`pipelines/flows/engines/`, `pipelines/flows/_common.py`, `pipelines/flows/_paths.py`, and
`pipelines/alerting_hooks.py` were deleted once nothing imported them; `pipelines/flows/main.py`
survives only as the `ingest_transform_publish` re-export of `pipelines.sqlmesh.flow`, because
`src/ogip/tasks/integrations.py` shells `python -m pipelines.flows.main` and that entry point
must stay importable at its historical path. `pipelines/dagster/flow.py` keeps Prefect as the
outer orchestrator with the dlt+dbt combo running *under* Dagster (`dg launch`) — the one
sub-project that is not a plain SQL runner.

## Consequences

- Positive: DQ declared once in `spec/sql` now has one real runtime effect on the production
  engine, not just on the comparison engines (dbt/Bruin) that happened to honor it already; an
  unknown check name is a build-time error instead of a check nobody notices was dropped.
- Positive: each run profile is independently deployable (`prefect deploy` from inside its own
  directory) and the plain-SQL profile is no longer a second-class citizen without a
  sub-project.
- Positive: the checks≠monitors boundary is structural, not a naming convention — monitors
  physically cannot appear in `spec/sql` `checks:` because the vocabulary that renders to
  audits does not recognize `freshness`/`row_count` names (they would raise `SqlSpecError`).
- **Known gap, prominent by design:** `make check` (`just check` → `just test` → `pytest -m
  "not integration and not e2e"`) never plans or applies SQLMesh against a real warehouse, so
  the generated `audits (...)` clauses are declared but not *evaluated* by the default gate.
  Only `uv run pytest src/tests/e2e/test_all_setups.py::test_base_setup_builds_and_produces_ml
  -k sqlmesh` (marked `e2e`, excluded from `make check`) or a live `prefect-sqlmesh` run
  actually executes them. This is not hypothetical: during this work, a `not_null(locale)`
  audit on `core.console_pricing` failed for every rawg game with no PSN listing (an
  unmatched-game LEFT JOIN produced an all-null row) — `make check` stayed green throughout,
  and the break was caught only by the e2e SQLMesh run (fixed in commit `d3caf76`, "fix(spec):
  console_pricing must not emit all-null rows for unmatched games"). Closing this gap — wiring
  an audit-executing step into `make check` or an equivalent fast pre-push gate — is not part
  of this decision and is open follow-up work.
- Negative: `dq/run.py` reporting monitors without executing them is a second, differently
  shaped version of the same gap (declared DQ with no enforcement in the default path) — tracked
  as Phase 4, not closed here.
- Neutral: `pipelines/_shared/engine_flow.py`, `pipelines/_shared/ingest.py`, and per-source
  scraper `@materialize` assets described in the original transform-expansion plan text did not
  ship as separate modules — `make_engine_flow` and the ingestion step stayed in `steps.py`.
  Behavior matches the plan's intent; the file split does not.

## Alternatives considered

- **Leave `to_sqlmesh` checks-silent, add a separate SQLMesh-only DQ layer.** Rejected — it
  would mean the SSoT (`spec/sql`) no longer describes production DQ, reintroducing exactly the
  per-engine hand-authored duplication ADR-0005 exists to prevent.
- **Fold row-count/freshness monitors into `checks:` for a single spec surface.** Rejected per
  ODTS §6: monitors and correctness checks have different failure semantics (a monitor evaluates
  against wall-clock/volume state, not a row-level predicate) and different homes by design; the
  spec explicitly excludes them from `checks:`.
- **Keep one `pipelines/flows/engines/` package instead of seven top-level directories.**
  Rejected — Prefect's `prefect deploy` model is directory-scoped (`prefect.yaml` +
  `deployments/`); a shared package cannot express "deploy only the sqlmesh setup" without
  either deploying everything or hand-filtering entrypoints, defeating the separation goal.
- **Wire the e2e SQLMesh audit run into `make check` now, closing the gap immediately.**
  Rejected for this change — the e2e suite drives real ingestion/warehouse builds per engine and
  is deliberately slow and marked `e2e` for that reason; folding it into the default gate is a
  separate decision about gate runtime budget, left open rather than made implicitly here.
