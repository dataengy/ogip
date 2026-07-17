# Runbook — Manual deploy to VPS

- **Trigger:** ship a new version to the VPS. **DevOps/infra is handled separately** ([ADR-0012](../adr/ADR-0012-github-ci-manual-vps-deploy.md)).
- **Owner:** maintainer with VPS access.
- **Scripts:** [`deploy/vps/`](../../deploy/vps/README.md) — every one takes `--dry-run` and `--help`.

## Preconditions

- CI green on the commit being deployed.
- SSH access to the VPS (as `root` for the first provision, as the service account after).
- `deploy.vps.host` set in [`config/config.yml`](../../config/config.yml), or `OGIP_VPS_HOST`
  exported. It is **blank by default on purpose** — the host is operator-specific, so nothing
  guesses it and every script aborts without it.
- Secrets present on the host in the gitignored `.env` ([ADR-0011](../adr/ADR-0011-minimal-secrets.md)).
  `deploy.sh` refuses to continue while a required slot is blank.

## First run only — provision the host

From your laptop (drives the box over ssh as root; idempotent, safe to re-run):

```bash
export OGIP_VPS_HOST=<ip-or-alias>
just vps-provision-dry     # preview every remote command
just vps-provision         # apt packages, Docker, uv, service account, checkout dir, clone
```

Then ssh in and fill `/opt/ogip/.env` (at minimum `RAWG_API_KEY`, `OGIP_PG_PASSWORD`).

## Steps — deploy

```bash
just vps-deploy-dry        # preview
just vps-deploy            # deploy deploy.vps.branch (default: main)
just vps-deploy <sha>      # deploy/pin a specific commit
```

`deploy.sh` runs **on the host** and does: preflight → fetch/checkout the ref → `uv sync` →
render `.env` → verify secrets → `prefect deploy` → `make up`. You can equally
`ssh <host>; cd /opt/ogip; deploy/vps/deploy.sh` — `just vps-deploy` is only the ssh bridge.

Preflight aborts **before** touching the checkout if a prerequisite is missing, rather than
half-deploying. Currently `integrations/prefect/deploy.py` does not exist yet, so a real
deploy stops there by design — see [`.ai/STATUS.md`](../../.ai/STATUS.md).

## Verify

```bash
just vps-smoke             # compose health · sample Prefect run · outputs · secret-leak scan
just vps-status            # deployed ref + containers + disk (read-only)
```

Non-zero exit from `vps-smoke` means **do not consider the deploy good** — roll back.

## Rollback

```bash
just vps-deploy <previous-sha>    # re-deploys that ref; detached checkout, no pull
just vps-smoke                    # confirm the rollback is healthy
```

`make down` on the host stops the services (volumes preserved).

## Escalation

- Host/network/provisioning/firewall problems → DevOps (separate ownership). `provision.sh`
  installs `ufw` but deliberately does not configure a port policy.
