# Runbooks

Operational procedures for OGIP. Deployment is **manual on a VPS** and **DevOps is handled
separately** ([ADR-0012](../adr/ADR-0012-github-ci-manual-vps-deploy.md)), so these runbooks are
the operational source of truth. Use [`_template.md`](_template.md) for new runbooks.

| Runbook | When | Status |
|---|---|---|
| [local-dev.md](local-dev.md) | Bootstrap + run the platform locally | draft |
| [run-pipeline.md](run-pipeline.md) | Run the daily pipeline / a `run-profile` in Docker + Prefect | draft |
| [deploy-vps.md](deploy-vps.md) | Manual deploy to the VPS | draft |
| [pipeline-failure.md](pipeline-failure.md) | Triage a failed Prefect flow / DQ gate | draft |
| backfill.md | Backfill / full-refresh a source | _planned_ |
| add-source.md | Add a new ingestion source | _planned_ |
| rotate-secrets.md | Rotate a secret | _planned_ |

Each runbook: **Trigger → Preconditions → Steps → Verify → Rollback → Escalation.**
