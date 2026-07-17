#!/usr/bin/env bash
# Shared helpers for the VPS scripts. Source at the top of each one.
#
# Settings resolve from config/config.yml (deploy.vps.*, the SSoT per AGENTS.md rule 3),
# with an OGIP_VPS_* env override per key. Nothing here invents a default: a missing
# setting aborts with the key name and both places it could have come from.
set -euo pipefail

VPS_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VPS_CONFIG="${VPS_REPO_ROOT}/config/config.yml"

log() { echo "[vps] $*"; }
warn() { echo "[vps] WARN: $*" >&2; }
die() {
  echo "[vps] ERROR: $*" >&2
  exit 1
}

# require_cmd <binary>... — abort unless every binary is on PATH.
require_cmd() {
  local cmd
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null 2>&1 || die "required command not found: ${cmd}"
  done
}

# setting <yaml-path> <ENV_OVERRIDE> — resolve one deploy.vps setting.
#
# Precedence: env override (if non-empty) > config/config.yml. A blank result is fatal,
# never a guess — deploying to a defaulted host is how you deploy to the wrong box.
setting() {
  local yaml_path="$1" env_name="$2" value
  if [[ -n "${!env_name-}" ]]; then
    printf '%s' "${!env_name}"
    return 0
  fi
  [[ -f "$VPS_CONFIG" ]] || die "settings file missing: ${VPS_CONFIG}"
  require_cmd yq
  value="$(yq -r "${yaml_path} // \"\"" "$VPS_CONFIG")"
  if [[ -z "$value" || "$value" == "null" ]]; then
    die "${yaml_path} is not set in ${VPS_CONFIG} (override: export ${env_name}=...)"
  fi
  printf '%s' "$value"
}

# vps_load_settings — populate the VPS_* globals every script reads.
vps_load_settings() {
  VPS_HOST="$(setting '.deploy.vps.host' OGIP_VPS_HOST)"
  VPS_USER="$(setting '.deploy.vps.user' OGIP_VPS_USER)"
  VPS_PORT="$(setting '.deploy.vps.port' OGIP_VPS_PORT)"
  VPS_PATH="$(setting '.deploy.vps.path' OGIP_VPS_PATH)"
  VPS_BRANCH="$(setting '.deploy.vps.branch' OGIP_VPS_BRANCH)"
  VPS_REPO_URL="$(setting '.deploy.vps.repo_url' OGIP_VPS_REPO_URL)"
  export VPS_HOST VPS_USER VPS_PORT VPS_PATH VPS_BRANCH VPS_REPO_URL
}

# vps_parse_flags "$@" — consume the flags every VPS script shares.
# Sets VPS_DRY_RUN (0|1) and leaves the rest in the VPS_ARGS array.
vps_parse_flags() {
  VPS_DRY_RUN=0
  VPS_ARGS=()
  local arg
  for arg in "$@"; do
    case "$arg" in
      --dry-run) VPS_DRY_RUN=1 ;;
      --help | -h)
        vps_usage
        exit 0
        ;;
      *) VPS_ARGS+=("$arg") ;;
    esac
  done
  export VPS_DRY_RUN
}

# vps_ssh <command...> — run a command on the VPS (or print it under --dry-run).
vps_ssh() {
  local target="${VPS_USER}@${VPS_HOST}"
  if [[ "$VPS_DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] ssh -p ${VPS_PORT} ${target} -- $*"
    return 0
  fi
  require_cmd ssh
  ssh -p "$VPS_PORT" -o StrictHostKeyChecking=accept-new "$target" -- "$@"
}

# vps_ssh_root <command...> — same, as root (provisioning only).
vps_ssh_root() {
  local target="root@${VPS_HOST}"
  if [[ "$VPS_DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] ssh -p ${VPS_PORT} ${target} -- $*"
    return 0
  fi
  require_cmd ssh
  ssh -p "$VPS_PORT" -o StrictHostKeyChecking=accept-new "$target" -- "$@"
}

# vps_run <command...> — run a command on the local host (or print it under --dry-run).
# Used by scripts that execute ON the VPS itself.
vps_run() {
  if [[ "$VPS_DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] $*"
    return 0
  fi
  "$@"
}

# vps_show_target — echo where we are about to act, so a wrong host is caught by eye.
vps_show_target() {
  log "target : ${VPS_USER}@${VPS_HOST}:${VPS_PORT}${VPS_PATH}"
  log "ref    : ${VPS_BRANCH} (${VPS_REPO_URL})"
  [[ "$VPS_DRY_RUN" -eq 1 ]] && log "mode   : DRY-RUN — nothing will be changed"
  return 0
}
