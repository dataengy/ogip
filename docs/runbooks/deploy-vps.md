# Runbook — Manual deploy to VPS

- **Trigger:** ship a new version to the VPS. **DevOps/infra is handled separately** ([ADR-0012](../adr/ADR-0012-github-ci-manual-vps-deploy.md)).
- **Owner:** maintainer with VPS access.

## Preconditions

- SSH access to the VPS; Docker + uv installed there; CI green on the commit being deployed.
- Secrets available on the host (gitignored `.env`, or an opt-in backend).

## Steps

1. SSH in; `git pull` the target commit in the repo checkout.
2. `deploy/vps/deploy.sh` — `uv sync` → `make render-env` → render secrets → `prefect deploy` → `make up`.
3. Trigger a smoke run: `just prefect-run ingest_transform_publish --params sample=true`.

## Verify

- Containers healthy; smoke Prefect run `Completed`; outputs written; no secret in logs.

## Rollback

- `git checkout <previous-sha>` + re-run `deploy/vps/deploy.sh`; `make down` to stop if needed.

## Escalation

- Host/network/provisioning problems → DevOps (separate ownership).
