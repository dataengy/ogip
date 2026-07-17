# Task — VPS deploy tooling (`deploy/vps/`)

**Status:** 🚧 in progress — scripts written, linted and dry-run verified; a real host deploy is
blocked on prerequisites owned by other lanes (see _Blocked on_).

Lane: `vps` (parallel-session lock object). Scope: `deploy/vps/`, the `vps-*` Justfile recipes,
and `config/config.yml → deploy.vps.*`. Decision record:
[ADR-0012](../../docs/adr/ADR-0012-github-ci-manual-vps-deploy.md) · runbook:
[deploy-vps.md](../../docs/runbooks/deploy-vps.md).

## Why

`docs/runbooks/deploy-vps.md` documented `deploy/vps/deploy.sh` step by step and ADR-0012
accepted it — but the script had never been written. The runbook described a script that did
not exist.

## Delivered

- `deploy/vps/lib.sh` — settings resolution (config SSoT + `OGIP_VPS_*` overrides), ssh
  wrappers, dry-run, fail-loud logging.
- `deploy/vps/provision.sh` — bare-host bootstrap over ssh (apt, Docker, uv, service account,
  checkout dir, first clone). Idempotent.
- `deploy/vps/deploy.sh` — runs on the host: fetch/checkout ref → `uv sync` → render `.env` →
  check secrets → `prefect deploy` → `make up`. Positional ref pins a rollback sha.
- `deploy/vps/check-secrets.sh` — blocks a deploy when a required `.env` slot is blank; never
  prints a value.
- `deploy/vps/smoke.sh` — post-deploy verification (compose health, Prefect run, outputs,
  secret-leak scan).
- `deploy/vps/remote.sh` · `status.sh` — drive the on-host scripts from the laptop; read-only status.
- Justfile: `vps-provision[-dry]` · `vps-deploy[-dry]` · `vps-smoke` · `vps-status`.
- `src/scripts/tasks_sync.py` — `.ai/tasks/*.md` → GitHub Issues (the `just tasks-sync` recipe
  had pointed at `integrations/github/tasks_sync.py`, which was never written).

## Verified

- `.ci/run.sh bash-lint` green (shellcheck + shfmt, 21 files); ruff + pyright strict clean.
- `provision.sh --dry-run` prints the full remote plan without opening a connection.
- Unset host aborts with an actionable message naming the key and both sources.
- `deploy.sh --dry-run` stops at preflight instead of half-deploying.
- `tasks_sync.py --dry-run` creates nothing (verified against the live tracker).

## Design notes

- **No setting defaults.** A blank host aborts. A defaulted host is how you deploy to the
  wrong box.
- **Preflight over partial deploy.** `deploy.sh` refuses to start when a prerequisite is
  absent, rather than fetching + syncing and dying at step 5.
- **Settings are not rendered into `.env`.** The host is per-operator; `.env` is for the
  application, not for how we reach the machine. `lib.sh` reads `config.yml` via `yq`, so the
  contended `config/.env-render.py` needed no change.

## Blocked on (other lanes)

A real deploy cannot succeed until these exist — `deploy.sh` preflight names both:

- `integrations/prefect/deploy.py` — `just prefect-deploy` (core-pipeline lane).
- `deploy/docker-compose.yml` — `make up` (landed 2026-07-17 by the obs/compose lane).

## Follow-ups

- Point `deploy.vps.host` at a real box and run `provision → deploy → smoke` end to end.
- `deploy.vps.compose_profiles` is declared but not yet consumed by `deploy.sh` (`make up`
  starts core services only) — wire it when the obs stack should come up on the host too.
- Firewall/port policy is deliberately unconfigured: DevOps-owned per ADR-0012.
