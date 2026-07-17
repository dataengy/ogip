#!/usr/bin/env bash
# Run one of the on-host scripts remotely — RUNS FROM YOUR LAPTOP.
#
# deploy.sh and smoke.sh are written to execute ON the VPS (that is what the runbook
# describes). This is the ssh bridge so you can drive them from here without a manual
# ssh + cd every time. It adds no logic of its own: same script, same flags, over ssh.
#
# Usage: deploy/vps/remote.sh <script.sh> [args...]
#   e.g. deploy/vps/remote.sh deploy.sh --dry-run abc1234

# shellcheck source=deploy/vps/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

vps_usage() {
  cat <<'USAGE'
Usage: deploy/vps/remote.sh <script.sh> [args...]

ssh's to the configured VPS and runs deploy/vps/<script.sh> inside the checkout.
Flags after the script name are passed through untouched (e.g. --dry-run).
USAGE
}

[[ $# -ge 1 ]] || {
  vps_usage
  die "no script given"
}

remote_script="$1"
shift

# --dry-run means "preview the remote run", so it must reach the remote script rather than
# stopping the ssh itself. Keep the flag in the payload and always open the connection.
VPS_DRY_RUN=0
vps_load_settings
vps_show_target

log "remote: deploy/vps/${remote_script} $*"
vps_ssh "cd '${VPS_PATH}' && bash 'deploy/vps/${remote_script}' $*"
