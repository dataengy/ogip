# Task — `make run-dagster-dbt`: expose the Prefect + dbt-under-Dagster setup

**Status:** 📋 ready · **Priority:** P1 (finalization phase B, step 9) ·
**Issue:** [#44](https://github.com/dataengy/ogip/issues/44)

The setup already exists: `experimental/pipelines/dagster/flow.py` — a Prefect flow that
shells `dg launch` (dlt asset + dbt subgraph) inside `experimental/orchestration/dagster_ogip`
(its own uv env) while Prefect keeps the ML/publish steps — wired to profile
`prefect-over-dagster` with a `make run-over-dagster` target. Missing: the alias named in the
finalization goal + a verified green run.

## Order of work

1. [ ] Makefile alias `run-dagster-dbt` → `run-over-dagster` (+ help line; README profiles table).
2. [ ] `uv sync` in `experimental/orchestration/dagster_ogip` (nested project, own venv).
3. [ ] Verify asset selections (`_DLT_ASSET`, `_DBT_SUBGRAPH`) against current dagster defs.
4. [ ] E2E run green: exit 0 + output row count on sample data.
5. [ ] Re-verify after PR #34 lands — flatten/warehouse-split may rename asset keys.

## Acceptance

`make run-dagster-dbt` green from a bare checkout (after `make render-env` + uv sync),
and the profile documented alongside the other run profiles.
