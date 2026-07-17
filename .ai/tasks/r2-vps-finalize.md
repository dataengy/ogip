# Task — Finalize R2 lake + VPS deploy (close the staged s3/vps handoffs)

**Status:** 📋 ready — every prerequisite is staged; all remaining edits sit in one lane ·
**Priority:** **P1**

Lane: `core-pipeline` (its previous lock is stale — see the STATUS lock audit; break and
re-acquire). Umbrella over the *remaining* items of
[s3-object-storage.md](s3-object-storage.md) and
[vps-deploy-tooling.md](vps-deploy-tooling.md) — those files keep the detail and history;
this one fixes the execution order.

## Why

The storage seam (`src/ogip/storage.py`, MinIO round-trip proven) and the VPS tooling
(`deploy/vps/*`, dry-run verified) exist, but the pipeline still runs only on the local FS
and a real deploy stops at preflight. Closing this makes the declared cloud story (R2 as
cloud of record — D2/D9) and the deploy story true end to end.

## Order of work

1. [ ] `ingestion/base/base_source.py` — swap the hardcoded local dlt destination for
       `dlt_filesystem_destination(data_dir)`; `run()` returns the dataset URL (`str`).
       _Coordinate: this file moved to the `ingestion` lane in the 2026-07-17 scope split._
2. [ ] Spec compiler + `spec/sql/raw/*.sql` — inject the lake root (from
       `ogip.storage.raw_bucket_url()`) instead of the literal `.run/data/...` path —
       **the real blocker** for any non-local backend.
3. [ ] `transform/sqlmesh/config.yaml` — DuckDB gateway: `extensions: [httpfs]` +
       `secrets:` interpolated from the `OGIP_S3_*` slots (config, not code).
4. [ ] `config/.env-render.py` — MinIO root + `OGIP_S3_*` dev defaults in `DEMO_DEFAULTS`
       (existing `OGIP_PG_PASSWORD` pattern), so a bare checkout runs `backend: minio`.
5. [ ] Verify: `make run` green with `backend: minio` locally + an e2e assertion; add the
       CI integration job with a MinIO service container (the round-trip test already
       skips cleanly when MinIO is absent).
6. [ ] **R2** — create the bucket, fill the `OGIP_S3_*` slots with the R2 endpoint/creds
       (code path identical to `s3`); record in
       [docs/architecture/storage.md](../../docs/architecture/storage.md).
7. [ ] `integrations/prefect/{deploy,trigger}.py` — unblocks `just prefect-deploy`,
       `deploy/vps/deploy.sh` step 5, and `deploy/vps/smoke.sh`.
8. [ ] Point `config/config.yml → deploy.vps.host` at a real box; run
       `just vps-provision → vps-deploy → vps-smoke` end to end.
9. [ ] While in the lane, optionally close the two obs handoffs (flow log file + obs port
       mapping — STATUS "Handoffs") so the deployed box is observable from day one.

## Acceptance

- `make run` green with `backend: r2` (real bucket) from a laptop: raw Parquet lands in
  R2 and SQLMesh reads it back via httpfs.
- `just vps-deploy && just vps-smoke` green against the real host.
- `make check` + CI green; the s3/vps handoff sections in STATUS collapse to closed.
