# ADR-0009 — Product = ML-ready outputs + Feature Store; no BI/semantic in core

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D6/D7/D8

## Context

Target users are Data Scientists, ML Engineers, and Analysts — not BI users. The platform's
product should serve modeling, not dashboards.

## Decision

The product is **ML-ready Parquet datasets** plus a **Feature Store (`fs_*`) layer**
(SQL-as-feature-store → parquet). JupyterLab demo notebooks are the primary DS interface;
`examples/load_datasets.py` shows programmatic loading. Semantic layers (MetricFlow/Cube) and
BI (Evidence) are **optional research** in `experimental/`; a dedicated FS tool (Feast/
Featureform) is an analyzed option, not a core dependency.

## Consequences

- Outputs are directly loadable (`pd/pl/duckdb.read_parquet`); no semantic API to operate.
- No online feature serving until a documented FS-tool adoption.

## Alternatives considered

- **BI-first + semantic layer** (OGAP) — reverted: wrong audience for this platform.
- **Dedicated feature store now** — deferred to `docs/comparisons/feature-store-tools.md`.
