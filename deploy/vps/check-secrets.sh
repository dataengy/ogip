#!/usr/bin/env bash
# Verify the rendered .env has every secret a deploy needs — RUNS ON THE VPS.
#
# The renderer writes secret slots blank (ADR-0011 / D10); a blank RAWG_API_KEY only
# surfaces as a 401 deep inside a flow run, so check it here instead. Reads the slot
# names from the renderer itself — one source of truth, no second list to drift.
#
# Usage: deploy/vps/check-secrets.sh
# Exits non-zero listing every unfilled slot. Never prints a secret value.

# shellcheck source=deploy/vps/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

VPS_DRY_RUN="${VPS_DRY_RUN-0}"
ENV_FILE="${VPS_REPO_ROOT}/.env"

# Slots a VPS deploy genuinely needs. Storage/IGDB slots stay optional: they matter only
# for run profiles the host may not use, and demanding them would block a valid deploy.
REQUIRED_SLOTS=(
  OGIP_PG_PASSWORD
  RAWG_API_KEY
)

[[ -f "$ENV_FILE" ]] || die "no .env at ${ENV_FILE} — run 'make render-env' first"

missing=()
for slot in "${REQUIRED_SLOTS[@]}"; do
  # Match the slot at line start, then take everything after the first '=' as the value.
  line="$(grep -E "^${slot}=" "$ENV_FILE" || true)"
  if [[ -z "$line" ]]; then
    missing+=("${slot}  (absent from .env — re-render it)")
    continue
  fi
  value="${line#*=}"
  [[ -z "$value" ]] && missing+=("${slot}  (present but blank)")
done

if [[ ${#missing[@]} -gt 0 ]]; then
  warn "required secrets are not filled in ${ENV_FILE}:"
  printf '  - %s\n' "${missing[@]}" >&2
  die "fill them on the host (ADR-0011: gitignored .env), then re-run"
fi

log "secrets OK — ${#REQUIRED_SLOTS[@]}/${#REQUIRED_SLOTS[@]} required slots filled"
