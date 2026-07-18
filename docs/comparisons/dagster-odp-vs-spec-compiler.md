# dagster-odp vs OGIP's spec→compiler (config-driven Dagster)

**Question asked:** can [dagster-odp](https://github.com/jonathanbhaskar/dagster-odp) be used for
this project? **Verdict: keep as a reference/comparison, do not adopt on the production path** —
it overlaps our existing spec-as-SSoT compiler and is Dagster-specific.

## What dagster-odp is

A configuration-driven framework (PyPI `dagster-odp` 0.1.4) that builds Dagster pipelines from
**YAML/JSON instead of Python**. You declare assets with a `task_type` (e.g. `url_file_download`,
`file_to_duckdb`, shell) and `depends_on`, and it generates the Dagster definitions. Pre-built
tasks for GCP/DuckDB/shell; integrations with dbt, dlt, Soda; config-based scheduling/partitions.

```yaml
assets:
  - asset_key: raw_data
    task_type: url_file_download
    params: { source_url: https://example.com/data.parquet, destination_file_path: ./raw.parquet }
  - asset_key: analyzed_data
    task_type: file_to_duckdb
    depends_on: [raw_data]
```

## Why it doesn't fit OGIP's production path

| Dimension | dagster-odp | OGIP today |
|---|---|---|
| Source of truth | its own YAML task DSL | `spec/` — **Bruin assets + ODCS** ([ADR-0005](../adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md)) |
| Engine coupling | **Dagster-specific** | engine-agnostic — the same spec compiles to **SQLMesh** (prod), dbt, plain-SQL, Bruin |
| Transform | task graph of pre-built tasks | portable SQL, compiled per engine |
| Overlap | it *is* a spec→Dagster compiler | we already have `src/ogip/spec_compile` (spec→SQLMesh/dbt) |

Adopting it would introduce a **second, competing config DSL** that only targets Dagster, undoing
the "one spec, many engines" thesis. OGIP already gets the config-driven benefit — the Dagster
alt-setup's dbt assets are generated from `spec/` via `to_dbt.py`.

## When it *would* be a good fit

- A Dagster-only shop with **no cross-engine requirement** that wants YAML pipelines without the
  spec-compiler machinery — dagster-odp is a lower-ceremony path there.
- As a **prototyping** tool for one-off Dagster ingestion graphs.

## Recommendation

Reference only. If we ever want to demonstrate it, it belongs in `experimental/`, fed from `spec/`
(a `spec → dagster-odp YAML` emitter) so `spec/` stays the SSoT — not as a parallel authoring surface.
