# `dq/` — data-quality executor

Runs the assertions declared in [`spec/dq`](../spec/) + Bruin column checks + ODCS SLAs
against the DuckDB warehouse. Severity: `error` blocks the flow, `warn` records to
`platform_meta.dq_results` and alerts ([ADR-0008](../docs/adr/ADR-0008-postgresql-roles.md)).

`run.py` — entry point (`just dq-check` / pre-push hook). Phase 0 = stub; rules arrive with
`spec/` (Phase 1) and the full executor in Phase 4.
