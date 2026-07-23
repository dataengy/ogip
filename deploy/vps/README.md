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

just vps-deploy-preview                 # host-free: validate deploy logic + preflight (no ssh)
just vps-deploy-dry                     # on-host preview (needs a reachable host)
just vps-deploy                         # deploy deploy.vps.branch
just vps-deploy abc1234                 # deploy/roll back to a specific sha
just vps-smoke                          # verify
just vps-status                         # containers + current ref
```

## Go live on Hetzner CX32

Recommended target: **Hetzner CX32** (4 vCPU / 8 GB / 80 GB NVMe, ~€7/mo) + **Cloudflare R2**
for the lake (zero egress). Ubuntu 24.04 LTS. Reachable UIs stay closed — reach Prefect/Grafana
over an SSH tunnel, not a public port (ADR-0012).

```bash
# 1. On Hetzner: create a CX32, image Ubuntu 24.04, add YOUR ssh key. Note the IP.
# 2. Point the tooling at it (never committed — operator-specific):
export OGIP_VPS_HOST=<the-ip>

# 3. Bootstrap once (idempotent: safe to re-run), then fill secrets on the box:
just vps-provision
ssh ogip@$OGIP_VPS_HOST 'nano /opt/ogip/.env'   # RAWG_API_KEY, R2 creds — ADR-0011

# 4. Deploy + verify:
just vps-deploy
just vps-smoke
```

Add `+2–4 GB swap` (DuckDB spikes are bursty) and `ufw allow 22` only. Russian-issued card?
Hetzner declines it — use **Timeweb Cloud** or **Selectel** (4 vCPU/8 GB ≈ 700–1200 ₽/mo);
`provision.sh` is host-agnostic Ubuntu, so nothing else changes.

## Known gaps (blocking a real deploy)

`deploy.sh` runs a **preflight** and refuses to start unless these exist — tracked in
[`.ai/STATUS.md`](../../.ai/STATUS.md):

- `integrations/prefect/deploy.py` — referenced by `just prefect-deploy`; **not yet written**
  (core-pipeline lane). This is the **only** remaining blocker; see the STATUS.md handoff for
  the Prefect run-model decision it carries.
- ~~`deploy/docker-compose.yml`~~ — **landed** with the compose/obs lane (2026-07-17).

Until `deploy.py` lands, `provision.sh` works end-to-end and `deploy.sh` stops cleanly at
preflight rather than half-deploying.
