# ADR-0016 — Orchestrator/transform responsibility boundary (no DQ duplication in Dagster)

- **Status:** Accepted
- **Date:** 2026-07-19
- **Relates to:** [ADR-0015](ADR-0015-dagster-alt-orchestration-dg-components.md) (Dagster alt-orchestration),
  [ADR-0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md) (spec SSoT + compiler), [ADR-0004](ADR-0004-sqlmesh-default-transform.md) (SQLMesh default transform)

## Context

The Dagster alt-orchestration (ADR-0015) wires dbt/dlt assets, jobs, schedules, sensors — and had
grown a hand-written Dagster `asset_check` (`market_features_nonempty_and_scored`) asserting the FS
feature contract (rows > 0, `popularity_score` not null). That assertion is *data quality*, and dbt
already owns DQ: `spec/` (Bruin `checks:`) compiles to dbt tests, `dbt build` runs them, and
`dagster-dbt` **automatically surfaces every dbt test as a Dagster asset check**. The hand-written
check was therefore a second, drifting copy of a rule that already lives in the SSoT.

## Decision

**Never implement in the orchestrator what the transform engine can do.** Data quality is expressed
once — as `spec/` checks compiled to dbt/SQLMesh tests — and the orchestrator only *surfaces* the
results. Concretely:

- A DQ assertion belongs in `spec/sql/*` (`checks:`), not in a Dagster `asset_check` or a Prefect task.
- `dagster-dbt` auto-mapping of dbt tests → asset checks is the sanctioned way DQ appears in the
  Dagster UI. No hand-written mirror.
- Reserve orchestrator-native checks strictly for what the engine genuinely cannot express
  (e.g. cross-system freshness, run-time SLAs), and note *why* in the check.
- The spec→dbt compiler must never silently drop an unmapped check — unknown check names warn.

This is the orchestration-specific corollary of the AGENTS.md rule "experimental engines *consume*
`spec/`, never duplicate it," and of the SSoT rule (ADR-0005).

## Consequences

- **+** One source of truth for DQ; no drift; portable across engines (same `spec/` drives SQLMesh
  and dbt). Fewer bespoke Dagster objects to maintain.
- **+** Fixed a latent bug the audit exposed: the compiler's check map knew only `not_null`/`unique`,
  so `non_negative` on `popularity_score` compiled to **nothing**. Now `non_negative` →
  `dbt_utils.accepted_range(min_value=0)`, and unmapped names warn instead of vanishing.
- **−** DQ visibility in Dagster now depends on `dbt build` having run (the dbt tests must materialize
  as asset checks); a pure asset-selection run that skips dbt won't show them. Acceptable — DQ is a
  property of the build, not of orchestration.
- The FS row-count assertion that the removed check also made is retained as the final gate in
  `experimental/orchestration/dagster_ogip/e2e/run_combo.sh`; expressing a table-level not-empty test
  in dbt (dbt_expectations) is a possible follow-up, deferred to avoid a Bruin-nonstandard construct.

## Verification

`dg check defs` clean; combo e2e green — `dbt build` runs 10 data tests (incl.
`not_null_market_features_popularity_score` and `dbt_utils_accepted_range_…`), and the run log shows
each evaluated as an `ASSET_CHECK_EVALUATION` on `fs/market_features`.
