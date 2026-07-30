#!/usr/bin/env bash
# CI gate for the Airbyte evaluation lane's Terraform (#41). fmt + validate ONLY.
#
# What CI CANNOT do: `plan`/`apply`. Those need a reachable Airbyte API — the
# airbyte_connector_configuration data sources read it live — and CI has no instance. That is a
# documented limitation, not a debt (see docs/techdebt/airbyte-lane.md), so real plans live on
# the opt-in local path. Here we prove the HCL is well-formed and canonically formatted, which
# is the honest most CI can assert offline.
#
# Self-skips when terraform is absent (keeps non-TF clones green); the lane is experimental and
# off the make path, so this runs only when the lane's terraform/ is present.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

TF_ROOT="experimental/ingestion/airbyte/terraform"

if [[ ! -d "$TF_ROOT" ]]; then
  log "no $TF_ROOT — airbyte lane absent, skip"
  exit 0
fi
if ! command -v terraform >/dev/null 2>&1; then
  log "terraform not installed — skip (install to enable this gate)"
  exit 0
fi

# 1) Formatting — canonical HCL across the whole lane tree.
log "terraform fmt -check ($TF_ROOT)"
terraform fmt -check -recursive "$TF_ROOT"

# 2) Validate each root that configures a provider (the module is validated transitively when a
#    root that calls it is validated). A root is any dir with a versions.tf that we can init with
#    -backend=false (no state, no network beyond the provider download).
mapfile -t roots < <(find "$TF_ROOT" -mindepth 2 -maxdepth 2 -name versions.tf -not -path '*/modules/*' -exec dirname {} \; | sort)
if [[ ${#roots[@]} -eq 0 ]]; then
  log "no variant roots yet — fmt-only"
  exit 0
fi

rc=0
for root in "${roots[@]}"; do
  log "validate: $root"
  (cd "$root" && terraform init -backend=false -input=false -no-color >/dev/null && terraform validate -no-color) || rc=1
done
exit "$rc"
