# ADR-0015 — Dagster alt-orchestration via `dg` Components (dbt + dlt + ingestr CDC)

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** [ADR-0007](ADR-0007-prefect-orchestration.md) (Prefect + runnable alt setups),
  [ADR-0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md) (spec SSoT + compiler), D1/D11

## Context

The `prefect-dagster-dlt-dbt` profile (A12) is one of the runnable alternative setups promised
by ADR-0007 — off the production path, to compare an asset-centric orchestrator against the
default Prefect+SQLMesh path. It needs a concrete, current implementation.

## Decision

Build it with the **modern Dagster approach — the `dg` CLI + Components** (`create-dagster
project`, `dg scaffold defs`, `dg check defs`, `dg launch --assets`), isolated in a
self-contained uv project under `experimental/orchestration/dagster_ogip/` so Dagster's deps
never touch the production env.

- **dbt** via `dagster_dbt.DbtProjectComponent` (`project: "{{ project_root }}/dbt"`,
  `select: "tag:daily"`). The dbt project is **generated from `spec/`** by `to_dbt.py` — spec/
  stays the SSoT: Bruin deps → `{{ ref() }}`, Bruin `tags` → dbt tags (drives `tag:daily`),
  Bruin `checks` → dbt tests, layer schemas via a `generate_schema_name` macro.
- **dlt** via `dagster_dlt.DltLoadCollectionComponent` — RAWG → raw Parquet, same Layer-0
  contract as the Prefect lane (`file_format="parquet"` pinned on the resource).
- **ingestr CDC** (D11) as a `@dg.asset` shelling out to `cdc/ingestr_cdc.sh` — the one CDC
  pipeline, from the Postgres landing zone.
- **dev** = SQLite in `DAGSTER_HOME`; **prod** = Postgres storage (env-refs only, ADR-0011),
  `QueuedRunCoordinator`.
- **Version:** Dagster **1.13.x** (there is no "Dagster 4"; 1.13.14 was latest at decision time).

## Consequences

- Asset-centric orchestration is demonstrable and **e2e-tested** (`e2e/run_combo.sh`, a separate
  `dagster-e2e` CI workflow) — source → FS layer in one run, incl. dbt tests as DQ.
- Two SSoT consumers (`to_sqlmesh.py`, `to_dbt.py`) must stay in step with `spec/` changes.
- The dbt asset key `raw/<table>` collides with the dlt asset's key, so the dbt raw model is
  left schema-unqualified (an external-registration view; the dlt asset is the real producer).

## Alternatives considered

- **Hand-written Dagster `@asset` graph** — rejected: Components are the current idiom and keep
  the dbt/dlt wiring declarative in `defs.yaml`.
- **A second, hand-maintained dbt project** — rejected: violates spec-as-SSoT; generate it.
