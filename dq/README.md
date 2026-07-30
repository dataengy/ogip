# `dq/` — data-quality executor

Runs the assertions declared in [`spec/dq`](../spec/) + Bruin column checks + ODCS SLAs
against the DuckDB warehouse. Severity: `error` blocks the flow, `warn` records to
`platform_meta.dq_results` and alerts ([ADR-0008](../docs/adr/ADR-0008-postgresql-roles.md)).

`run.py` — entry point (`just dq-check` / pre-push hook). Phase 0 = stub; rules arrive with
`spec/` (Phase 1) and the full executor in Phase 4.

Monitors (row-count floors, freshness) are now declared in
[`spec/dq/policy.yml`](../spec/dq/policy.yml) — the ODTS/ODOS designated home for them (neither
standard has a slot for this class of check). `run.py` loads that policy and reports a summary
(count by type/severity); it does not yet execute the monitors against the warehouse — that
lands with the Phase-4 executor.
