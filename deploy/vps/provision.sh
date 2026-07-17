#!/usr/bin/env bash
# First-run host bootstrap — RUNS FROM YOUR LAPTOP, drives the VPS over ssh as root.
#
# Brings a bare Ubuntu/Debian box to the point where deploy.sh can run: packages, Docker,
# uv, an unprivileged service account, the checkout dir, and a first clone. Idempotent —
# safe to re-run; each step checks before it acts.
#
# Usage: deploy/vps/provision.sh [--dry-run]
# See docs/runbooks/deploy-vps.md · ADR-0012 (infra/DevOps is owned separately).

# shellcheck source=deploy/vps/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

vps_usage() {
  cat <<'USAGE'
Usage: deploy/vps/provision.sh [--dry-run]

Bootstraps a bare VPS over ssh (as root): apt packages, Docker Engine + compose plugin,
uv, the service account, and the initial clone. Idempotent.

  --dry-run   print every remote command instead of running it
  --help      this text

Settings: config/config.yml -> deploy.vps.* (override with OGIP_VPS_HOST / _USER / ...).
USAGE
}

vps_parse_flags "$@"
vps_load_settings
vps_show_target

log "step 1/6 — base packages"
vps_ssh_root bash -euo pipefail -c '
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl git ufw
'

log "step 2/6 — Docker Engine + compose plugin (official convenience script, idempotent)"
# shellcheck disable=SC2016  # $(docker --version) is for the REMOTE shell — must not expand here.
vps_ssh_root bash -euo pipefail -c '
  if command -v docker >/dev/null 2>&1; then
    echo "docker already present: $(docker --version)"
  else
    curl -fsSL https://get.docker.com | sh
  fi
  docker compose version
'

log "step 3/6 — service account ${VPS_USER} (unprivileged, docker group)"
vps_ssh_root bash -euo pipefail -c "
  if id -u '${VPS_USER}' >/dev/null 2>&1; then
    echo 'user ${VPS_USER} already exists'
  else
    useradd --create-home --shell /bin/bash '${VPS_USER}'
  fi
  usermod -aG docker '${VPS_USER}'
  # Reuse the operator's authorized_keys so the same key logs in as the service account.
  install -d -m 700 -o '${VPS_USER}' -g '${VPS_USER}' '/home/${VPS_USER}/.ssh'
  if [[ -f /root/.ssh/authorized_keys ]]; then
    install -m 600 -o '${VPS_USER}' -g '${VPS_USER}' \
      /root/.ssh/authorized_keys '/home/${VPS_USER}/.ssh/authorized_keys'
  fi
"

log "step 4/6 — checkout dir ${VPS_PATH}"
vps_ssh_root bash -euo pipefail -c "
  install -d -m 755 -o '${VPS_USER}' -g '${VPS_USER}' '${VPS_PATH}'
"

log "step 5/6 — uv (installed for ${VPS_USER}, not root)"
# shellcheck disable=SC2016  # $HOME must resolve to the service account's home, remotely.
vps_ssh_root su - "${VPS_USER}" -c '
  if command -v uv >/dev/null 2>&1 || [[ -x "$HOME/.local/bin/uv" ]]; then
    echo "uv already present"
  else
    curl -fsSL https://astral.sh/uv/install.sh | sh
  fi
'

log "step 6/6 — first clone of ${VPS_REPO_URL} (${VPS_BRANCH})"
vps_ssh_root su - "${VPS_USER}" -c "
  if [[ -d '${VPS_PATH}/.git' ]]; then
    echo 'repo already cloned at ${VPS_PATH}'
  else
    git clone --branch '${VPS_BRANCH}' '${VPS_REPO_URL}' '${VPS_PATH}'
  fi
"

log "provision complete."
log "NEXT: put secrets in ${VPS_PATH}/.env on the host (RAWG_API_KEY, ...), then: just vps-deploy"
log "NOTE: firewall (ufw) is installed but NOT configured — port policy is DevOps-owned (ADR-0012)."
