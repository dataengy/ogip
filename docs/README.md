# OGIP — Documentation

**OGIP · Open Games Intelligence Platform** — a Market Intelligence Platform that turns
public gaming-market data into **ML-ready Parquet datasets** for Data Scientists, ML
Engineers, and Analysts.

| Doc | What |
|---|---|
| [architecture/](architecture/) | System design: [overview](architecture/overview.md) + per-topic sub-docs |
| [adr/](adr/) | Architecture Decision Records (ADR-0001…, indexed) |
| [runbooks/](runbooks/) | Operational procedures (local dev, run pipeline, deploy, incident triage) |
| [ROADMAP.md](ROADMAP.md) | Delivery phases |
| DATASETS.md | ML-ready output catalog _(Phase 5)_ |
| [CHANGELOG.md](CHANGELOG.md) | Notable changes |
| `comparisons/` | Educational, isolated research: `dbt-vs-sqlmesh` · `dbt-vs-bruin` · `sqlmesh-vs-bruin` · `plain-sql-vs-frameworks` · `iceberg-vs-ducklake` · `dlt-vs-ingestr` (incl. CDC) · `feature-store-tools` · `visualizers-evidence` · `secrets-management` · `modeling-techniques` _(Phase 9)_ |

The master creation plan lives in [.ai/PLAN.md](../.ai/PLAN.md); agent rules in
[.ai/AGENTS.md](../.ai/AGENTS.md).
