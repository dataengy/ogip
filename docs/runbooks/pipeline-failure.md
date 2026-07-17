# Runbook — Pipeline failure triage

- **Trigger:** a Prefect flow run failed, or a DQ `error` check blocked the pipeline.
- **Owner:** on-call operator. **Urgency:** depends on staleness SLA.

## Preconditions

- Access to Prefect logs/UI and `platform_meta` in Postgres.

## Steps

1. Identify the failed task in the Prefect run (UI or `just prefect-logs <run-id>`).
2. Classify:
   - **Ingestion** (dlt/ingestr, rate-limit, auth) → check source watermark + `platform_meta.ingestion_runs`.
   - **Transform** (SQLMesh) → read the model error; check upstream freshness; `just sqlmesh-audit`.
   - **DQ gate** (`error`) → inspect `platform_meta.dq_results`; decide quarantine vs fix.
3. Fix root cause; re-run the flow (idempotent — immutable raw + deterministic transforms).

## Verify

- Re-run `Completed`; DQ green; outputs refreshed.

## Rollback

- If a bad build shipped: `make warehouse-reset` then re-run from the last good raw load.

## Escalation

- Host/service outages → DevOps (separate). Data-source outages → note in the run + retry with backoff.
