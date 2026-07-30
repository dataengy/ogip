#!/usr/bin/env bash
# OGIP — mint Airbyte OSS API credentials into the rendered .env (evaluation lane, #41).
#
# OSS authenticates with CLIENT CREDENTIALS and a 15-minute access-token TTL, so the Terraform
# provider is handed client_id/client_secret and refreshes itself. A static bearer token would
# expire mid-apply -- never wire one.
#
# AIRBYTE_CLIENT_ID/SECRET are declared secret slots in config/.env-render.py, which is
# merge-safe: a later `make render-env` PRESERVES the values written here.
#
# Secrets are never echoed: only which slots were filled.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

log() { echo "[airbyte] $*"; }
die() {
  echo "[airbyte] ERROR: $*" >&2
  exit 1
}

command -v abctl >/dev/null 2>&1 || die "abctl not installed: brew tap airbytehq/tap && brew install abctl"
[[ -f .env ]] || die ".env missing — run \`make render-env\` first."

raw="$(abctl local credentials 2>/dev/null)" || die "\`abctl local credentials\` failed — is the instance up (./up.sh)?"

# abctl prints a labelled block; tolerate label/spacing drift across versions rather than
# assuming a fixed line order.
client_id="$(printf '%s\n' "$raw" | grep -iE '^[[:space:]]*client[-_ ]?id' | head -1 | sed -E 's/.*[:=][[:space:]]*//')"
client_secret="$(printf '%s\n' "$raw" | grep -iE '^[[:space:]]*client[-_ ]?secret' | head -1 | sed -E 's/.*[:=][[:space:]]*//')"

[[ -n "$client_id" ]] || die "could not parse Client-Id from \`abctl local credentials\` output."
[[ -n "$client_secret" ]] || die "could not parse Client-Secret from \`abctl local credentials\` output."

# In-place slot fill. The slots already exist (blank) in the rendered .env; replace their
# values rather than appending duplicates that would shadow each other on source.
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
AB_ID="$client_id" AB_SECRET="$client_secret" awk '
  /^AIRBYTE_CLIENT_ID=/     { print "AIRBYTE_CLIENT_ID=" ENVIRON["AB_ID"];     next }
  /^AIRBYTE_CLIENT_SECRET=/ { print "AIRBYTE_CLIENT_SECRET=" ENVIRON["AB_SECRET"]; next }
  { print }
' .env >"$tmp"

grep -q '^AIRBYTE_CLIENT_ID=.\+' "$tmp" || die "AIRBYTE_CLIENT_ID slot not present in .env — re-run \`make render-env\`."
grep -q '^AIRBYTE_CLIENT_SECRET=.\+' "$tmp" || die "AIRBYTE_CLIENT_SECRET slot not present in .env — re-run \`make render-env\`."

cat "$tmp" >.env
log "filled AIRBYTE_CLIENT_ID and AIRBYTE_CLIENT_SECRET in .env (values not printed)."
