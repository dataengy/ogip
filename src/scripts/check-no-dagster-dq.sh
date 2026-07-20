#!/usr/bin/env bash
# check-no-dagster-dq.sh — enforce ADR-0017: no hand-written Dagster asset_check that duplicates
# a dbt/SQLMesh test. dagster-dbt already surfaces every dbt test as an asset check; a bespoke
# `@dg.asset_check` in source is almost always a drifting second copy of a DQ rule that belongs
# in spec/. This guard fails CI/pre-commit when one appears WITHOUT an explicit, reasoned waiver.
#
# Waiver: put `dagster-dq-ok:` followed by a reason on the line above the decorator, for the rare
# check the transform engine genuinely cannot express (cross-system freshness, run SLAs). Example:
#     # dagster-dq-ok: cross-source freshness — dbt cannot see the upstream API's clock
#     @dg.asset_check(asset=K_FS, ...)
#
# Usage: check-no-dagster-dq.sh [root]   (default root: the Dagster subproject under this repo)
# Exit:  0 clean/all-waived · 1 an unwaived asset_check was found · 4 bad usage.
set -euo pipefail

log() { echo "[no-dagster-dq] $*"; }
die() {
  echo "[no-dagster-dq] ERROR: $*" >&2
  exit 4
}

REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git work tree"
ROOT="${1:-$REPO/experimental/orchestration/dagster_ogip/src}"
[[ -d "$ROOT" ]] || die "not a directory: $ROOT"

# Match the decorator in either import style: `@dg.asset_check` or a bare `@asset_check`.
pattern='^[[:space:]]*@(dg\.)?asset_check\b'
violations=0

while IFS= read -r hit; do
  file="${hit%%:*}"
  rest="${hit#*:}"
  line="${rest%%:*}"
  # A waiver is `dagster-dq-ok:` on the immediately preceding line.
  prev=$((line - 1))
  if [[ "$prev" -ge 1 ]] && sed -n "${prev}p" "$file" | grep -q 'dagster-dq-ok:'; then
    log "waived ${file#"$REPO"/}:$line ($(sed -n "${prev}p" "$file" | sed 's/.*dagster-dq-ok://; s/^[[:space:]]*//'))"
    continue
  fi
  log "VIOLATION ${file#"$REPO"/}:$line — hand-written Dagster asset_check (see ADR-0017)"
  violations=$((violations + 1))
done < <(grep -rnE "$pattern" "$ROOT" --include='*.py' --exclude-dir=__pycache__ 2>/dev/null || true)

if [[ "$violations" -gt 0 ]]; then
  log "$violations unwaived asset_check(s). Express the DQ as a spec/ check (→ dbt/SQLMesh test),"
  log "or add a '# dagster-dq-ok: <reason>' line above the decorator if the engine truly cannot."
  exit 1
fi
log "clean — no hand-written Dagster DQ (ADR-0017 satisfied)"
