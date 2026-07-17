# Runbook — Run the pipeline (Docker + Prefect)

- **Trigger:** run the daily pipeline, a backfill, or an alternative `run-profile`.
- **Owner:** any contributor / operator.

## Preconditions

- `make up` services healthy; `.env` rendered; source API keys present in `.env` for real extraction.

## Steps

1. Choose a profile (default is production): `just run-profile prefect-sqlmesh`
   (alts: `prefect-sql`, `prefect-bruin`, `prefect-dbt`, `prefect-sqlmesh-over-dbt`, `prefect-dagster-dlt-dbt`).
2. Deploy/trigger the Prefect flow: `just prefect-deploy && just prefect-run ingest_transform_publish`
   (wraps `integrations/prefect/` — Prefect CLI/API).
3. Follow the run in the Prefect UI (server profile) or the flow logs (ephemeral).

## Verify

- Prefect run state = `Completed`; `.run/outputs/*.parquet` refreshed; DQ gate passed
  (`platform_meta.dq_results`); notebook / Evidence page renders the new data.

## Rollback

- Raw is immutable — re-run is idempotent. To discard a bad warehouse build: `make warehouse-reset`.

## Escalation

- A red run → [pipeline-failure.md](pipeline-failure.md).
