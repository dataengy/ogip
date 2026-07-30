# ADR-0020 — dbt (primary) + Bruin (co-primary) transform engines; SQLMesh becomes a comparison setup

- **Status:** Accepted
- **Date:** 2026-07-30
- **Relates to:** PLAN decision D5 · [ADR-0004](ADR-0004-sqlmesh-default-transform-engine.md) ·
  [ADR-0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md) · re-root plan
  ([docs/superpowers/plans/2026-07-24-reroot-dbt-bruin-primary-candidates.md](../superpowers/plans/2026-07-24-reroot-dbt-bruin-primary-candidates.md),
  [#40](https://github.com/dataengy/ogip/issues/40))

## Context

D5/ADR-0004 made SQLMesh the default transform engine, with dbt/Bruin/plain-SQL as generated
comparison projects. Since then the balance of evidence shifted (re-root candidates doc, #40):

- Every engine project is **generated from `spec/`** (ADR-0005), so "primary" is a compiler
  and wiring flag, not a rewrite — the demotion/promotion cost is small by design.
- **dbt** is the engine the showcase's audience reads fluently, and the repo's richest engine
  integrations already live on the dbt path (dbt-hub packages, project-evaluator, dbt-native
  DQ tests, the Dagster `DbtProjectComponent`, SQLMesh-over-dbt).
- **Bruin** is the zero-translation path: `spec/sql` *is* Bruin/`@odts`-shaped, and Bruin runs
  it natively on DuckDB — keeping one engine that consumes the spec without a rendering step
  keeps the compiler honest.
- Re-root Tasks 1–3 already landed the mechanics: dbt+bruin are `DEFAULT_ENGINES` in the
  compiler, the five demoted Prefect sub-projects moved to `experimental/pipelines/`.

## Decision

We make **dbt the primary** and **Bruin the co-primary** transform engines. The default run
profile is `prefect-dbt` (`make run` → `run-dbt`); `prefect-bruin` and the
`prefect-over-dagster` combo (Prefect + dbt-under-Dagster) are the other two first-class,
demo-guaranteed setups. SQLMesh, plain-SQL, OpenDBT and SQLMesh-over-dbt profiles carry
`experimental: true` in `config/config.yml`, print an EXPERIMENTAL banner when run, and their
e2e sits behind `OGIP_E2E_ALL_ENGINES=1`. Default gates (`make check`, CI e2e) exercise
dbt + Bruin.

## Consequences

- The demo story is legible to its audience (dbt) while proving the spec-first design (Bruin
  runs the spec natively; both are regenerated, never hand-forked).
- Gates get cheaper and sharper: 2 primary engines instead of 5 half-gated ones.
- ADR-0019's DQ projection keeps working — `columns[].checks` project into dbt tests on the
  primary path; the SQLMesh-audits rendering remains exercised only under the full-matrix flag.
- Docs/tests carrying the SQLMesh-primary claim must flip in the same change set
  (AGENTS.md hard rules, `config/config.yml`, `Makefile`, `test_wiring`, `test_all_setups`,
  READMEs — re-root T4–T7).
- ADR-0004 stays Accepted as history; this ADR refines its "default engine" clause the same
  way ADR-0016 refines ADR-0005's format clause.

## Alternatives considered

- **Keep SQLMesh primary** — rejected: the audience-legibility and ecosystem-demo value sit
  on the dbt path; SQLMesh stays as a maintained comparison setup, not deleted.
- **Bruin-only primary** — rejected: loses the industry-standard demonstration; Bruin alone
  under-uses the generated-project machinery the compiler exists to show.
- **Dagster-orchestrated dbt as the default** — rejected: Dagster remains the alternative
  orchestration showcase (`prefect-over-dagster` seam + standalone `dagster_ogip`), Prefect
  stays the platform orchestrator (D3/D9).
