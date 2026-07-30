#!/usr/bin/env bash
# Create (or reuse) the Hetzner Cloud box that provision.sh then bootstraps.
#
# This is the step BEFORE provision.sh: it turns "I have a Hetzner account" into "I have an
# IP". provision.sh already does the bootstrap properly (unprivileged service account, ufw,
# docker, uv), so this deliberately stops at a reachable box and prints the export line —
# it does not install anything.
#
# Everything is idempotent and keyed by server NAME: run it twice and the second run reuses
# the existing server instead of billing you for a second one.
#
# Usage:
#   deploy/vps/hetzner.sh [--dry-run]
#   just vps-hetzner            # or vps-hetzner-dry
#
# Settings: config/config.yml → deploy.hetzner.* (each overridable via OGIP_HETZNER_*).
# Token: asked once through the macOS GUI (src/scripts/ask-secret-gui.sh) and kept in .env.
#
# Exit: 0 server ready · 1 aborted (no token / ssh never came up / API error)

# shellcheck source=deploy/vps/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

vps_parse_flags "$@"
require_cmd curl jq ssh ssh-keygen

NAME="$(setting '.deploy.hetzner.server_name' OGIP_HETZNER_SERVER_NAME)"
TYPE="$(setting '.deploy.hetzner.server_type' OGIP_HETZNER_SERVER_TYPE)"
IMAGE="$(setting '.deploy.hetzner.image' OGIP_HETZNER_IMAGE)"
LOCATION="$(setting '.deploy.hetzner.location' OGIP_HETZNER_LOCATION)"
API="$(setting '.deploy.hetzner.api_base' OGIP_HETZNER_API_BASE)"
TOKEN_URL="$(setting '.deploy.hetzner.token_url' OGIP_HETZNER_TOKEN_URL)"
SSH_KEY_PATH="$(setting '.deploy.hetzner.ssh_key_path' OGIP_HETZNER_SSH_KEY_PATH)"
SSH_KEY_PATH="${SSH_KEY_PATH/#\~/$HOME}"
SSH_KEY_NAME="$(setting '.deploy.hetzner.ssh_key_name' OGIP_HETZNER_SSH_KEY_NAME)"
WAIT_SECS="$(setting '.deploy.hetzner.ssh_wait_secs' OGIP_HETZNER_SSH_WAIT_SECS)"

log "server : ${NAME} (${TYPE}, ${IMAGE}, ${LOCATION})"
[[ "$VPS_DRY_RUN" -eq 1 ]] && log "mode   : DRY-RUN — nothing will be created"

# ── token ────────────────────────────────────────────────────────────────────────────────
# A Read&Write token can create and destroy billable servers, so it is never printed and
# never passed on a command line. Dry-run must not pop a dialog: previewing is not consenting.
if [[ "$VPS_DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] ensure HETZNER_API_TOKEN via GUI ask (${TOKEN_URL})"
  TOKEN="dry-run-placeholder"
else
  bash "${VPS_REPO_ROOT}/src/scripts/ask-secret-gui.sh" HETZNER_API_TOKEN "$TOKEN_URL" \
    "Hetzner Cloud API token — project → Security → API tokens → Generate (Read & Write)" ||
    die "no Hetzner API token — aborting"
  TOKEN="$(grep -m1 '^HETZNER_API_TOKEN=' "${VPS_REPO_ROOT}/.env" 2>/dev/null | cut -d= -f2- || true)"
  [[ -n "$TOKEN" ]] || die "HETZNER_API_TOKEN missing from .env after the prompt"
fi

# curl reads the auth header from a 0600 file instead of -H: an argument would be visible to
# every process on the machine via `ps`. Removed on any exit, including failure.
AUTH_CONF="$(mktemp -t ogip-hz)"
chmod 600 "$AUTH_CONF"
trap 'rm -f "$AUTH_CONF"' EXIT
printf 'header = "Authorization: Bearer %s"\n' "$TOKEN" >"$AUTH_CONF"

hz() { curl -fsS --config "$AUTH_CONF" -H 'Content-Type: application/json' "$@"; }

# ── ssh key ──────────────────────────────────────────────────────────────────────────────
# Matched by fingerprint, not name: the same key uploaded under a different name would
# otherwise be registered twice and the server would accept a key you did not mean to use.
[[ -f "$SSH_KEY_PATH" ]] || die "ssh public key not found: ${SSH_KEY_PATH} (ssh-keygen -t ed25519)"
FINGERPRINT="$(ssh-keygen -lf "$SSH_KEY_PATH" -E md5 | awk '{print $2}' | sed 's/^MD5://')"

if [[ "$VPS_DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] ensure ssh key ${FINGERPRINT} (${SSH_KEY_NAME}) registered at ${API}/ssh_keys"
else
  if hz "${API}/ssh_keys" | jq -e --arg fp "$FINGERPRINT" '.ssh_keys[] | select(.fingerprint==$fp)' >/dev/null; then
    log "ssh key already registered (${FINGERPRINT})"
  else
    log "registering ssh key ${SSH_KEY_NAME} (${FINGERPRINT})"
    hz -X POST "${API}/ssh_keys" \
      -d "$(jq -n --arg n "$SSH_KEY_NAME" --rawfile k "$SSH_KEY_PATH" '{name:$n, public_key:$k}')" >/dev/null
  fi
fi

# ── server ───────────────────────────────────────────────────────────────────────────────
if [[ "$VPS_DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] GET ${API}/servers?name=${NAME} → create if absent, reuse if present"
  echo "[dry-run] then wait up to ${WAIT_SECS}s for ssh, and print the OGIP_VPS_HOST export"
  log "dry-run complete — no server created, no token requested"
  exit 0
fi

IP="$(hz "${API}/servers?name=${NAME}" | jq -r '.servers[0].public_net.ipv4.ip // empty')"
if [[ -n "$IP" ]]; then
  log "server ${NAME} already exists → reusing ${IP} (not billing a second one)"
else
  log "creating ${NAME} — this starts billing"
  IP="$(hz -X POST "${API}/servers" \
    -d "$(jq -n --arg n "$NAME" --arg t "$TYPE" --arg i "$IMAGE" --arg l "$LOCATION" --arg k "$SSH_KEY_NAME" \
      '{name:$n, server_type:$t, image:$i, location:$l, ssh_keys:[$k], start_after_create:true}')" |
    jq -r '.server.public_net.ipv4.ip // empty')"
  [[ -n "$IP" ]] || die "server created but the API returned no IPv4 — check the Hetzner console"
fi

# ── wait for ssh ─────────────────────────────────────────────────────────────────────────
# Bounded, unlike the obvious `until ssh …; do sleep; done`: a box that never boots would
# otherwise hang the deploy forever with no diagnosis.
log "waiting for ssh on ${IP} (up to ${WAIT_SECS}s)"
deadline=$((SECONDS + WAIT_SECS))
until ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 -o BatchMode=yes \
  "root@${IP}" true 2>/dev/null; do
  if [[ $SECONDS -ge $deadline ]]; then
    die "ssh on ${IP} did not answer within ${WAIT_SECS}s — the server exists; check the console, then re-run (it will reuse, not recreate)"
  fi
  sleep 5
done

log "server ready: ${NAME} @ ${IP}"
cat <<EOF

Next — bootstrap it with the existing tooling:

  export OGIP_VPS_HOST=${IP}
  just vps-provision              # unprivileged ogip account, docker, ufw, uv
  ssh ogip@${IP} 'nano /opt/ogip/.env'
  just vps-deploy && just vps-smoke
EOF
