# `deploy/vps/` — manual VPS deploy

Scripts behind [`docs/runbooks/deploy-vps.md`](../../docs/runbooks/deploy-vps.md).
Deployment is **manual and runbook-driven**; infra/DevOps is owned separately
([ADR-0012](../../docs/adr/ADR-0012-github-ci-manual-vps-deploy.md)). No k8s, no Terraform.

## Scripts

| Script | Runs on | Purpose |
|---|---|---|
| `lib.sh` | — | Shared helpers: settings resolution, `ssh` wrappers, dry-run, logging. Sourced, not run. |
| `provision.sh` | **your laptop** (drives the host as root) | First-run bootstrap: apt packages, Docker, uv, service account, checkout dir, first clone. Idempotent. |
| `deploy.sh` | **the VPS** | Fetch/checkout a ref → `uv sync` → render `.env` → check secrets → `prefect deploy` → `make up`. Idempotent. |
| `check-secrets.sh` | **the VPS** | Fails if a required secret slot in `.env` is blank. Called by `deploy.sh`; never prints values. |
| `smoke.sh` | **the VPS** | Post-deploy verification: compose health, sample Prefect run, outputs, secret-leak scan. |

Every script takes `--dry-run` (print commands, change nothing) and `--help`.

## Settings

Resolved by `lib.sh` from `config/config.yml → deploy.vps.*` — the SSoT
([AGENTS.md](../../.ai/AGENTS.md) rule 3). Each key takes an `OGIP_VPS_*` env override:

| Setting | Env override | Default | Notes |
|---|---|---|---|
| `host` | `OGIP_VPS_HOST` | _(blank)_ | IP / hostname / `ssh_config` alias. **Blank on purpose** — operator-specific, never committed. |
| `user` | `OGIP_VPS_USER` | `ogip` | Unprivileged service account created by `provision.sh`. |
| `port` | `OGIP_VPS_PORT` | `22` | ssh port. |
| `path` | `OGIP_VPS_PATH` | `/opt/ogip` | Checkout location on the host. |
| `branch` | `OGIP_VPS_BRANCH` | `main` | Git ref to deploy. |
| `repo_url` | `OGIP_VPS_REPO_URL` | `github.com/dataengy/ogip` | Clone URL. |

A missing or blank setting **aborts** with the key name and both places it could come from —
nothing here falls back to a guess, because a defaulted host is how you deploy to the wrong box.

These values are read straight from `config.yml` by `yq` and are deliberately **not** rendered
into `.env`: the host is per-operator, and `.env` is for the application, not for the way we
reach the machine.

## Usage

```bash
export OGIP_VPS_HOST=203.0.113.10       # or set deploy.vps.host in config/config.yml

just vps-provision-dry                  # preview the bootstrap
just vps-provision                      # bootstrap the box (once)

# fill secrets on the host: ssh in, edit /opt/ogip/.env  (ADR-0011: gitignored .env)

just vps-deploy-dry                     # preview the deploy
just vps-deploy                         # deploy deploy.vps.branch
just vps-deploy abc1234                 # deploy/roll back to a specific sha
just vps-smoke                          # verify
just vps-status                         # containers + current ref
```

## Known gaps (blocking a real deploy)

`deploy.sh` runs a **preflight** and refuses to start unless these exist — they are owned by
other lanes and tracked in [`.ai/STATUS.md`](../../.ai/STATUS.md):

- `integrations/prefect/deploy.py` — referenced by `just prefect-deploy`; **not yet written**.
- `deploy/docker-compose.yml` — referenced by `make up`; **not yet written**.

Until both land, `provision.sh` works end-to-end and `deploy.sh` stops cleanly at preflight
rather than half-deploying.
