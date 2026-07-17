# Architecture

The architecture docs for OGIP. Start with [`overview.md`](overview.md); point-in-time
decisions live as [ADRs](../adr/); the full creation plan is [`.ai/PLAN.md`](../../.ai/PLAN.md).

| Doc | What | Status |
|---|---|---|
| [overview.md](overview.md) | System context, pipeline, layer stack, component map | draft |
| data-flow.md | End-to-end data flow (source → landing → raw → warehouse → outputs) | _Phase 1_ |
| ingestion.md | `BaseSource` family, dlt/ingestr, Postgres landing, watermarks | _Phase 2_ |
| transformation.md | Spec → SQLMesh compiler, layer builds, portability | _Phase 3_ |
| storage.md | Parquet/PyArrow, FS/R2/MinIO/S3, DuckDB warehouse | _Phase 3_ |
| data-quality.md | Contracts (ODCS), assertions, freshness, RI, severity | _Phase 4_ |
| observability.md | Logging, metrics (VictoriaMetrics), Loki, Grafana, alerts | _Phase 7_ |

Until a sub-doc exists, its topic is covered by the matching section of
[`.ai/PLAN.md`](../../.ai/PLAN.md) Part A.
