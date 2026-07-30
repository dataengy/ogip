#!/usr/bin/env bash
# Assert large test datasets are LFS pointers, not raw blobs — the CI half of the rule.
#
# .gitattributes routes binary dataset formats on fixture paths through LFS, but attributes
# only act at `git add` time: a file added before the pattern existed, added with
# `--no-verify`, or added in a clone that never ran `git lfs install` lands as a RAW blob —
# and a blob in history is forever (rewriting means force-pushing a branch four agent
# sessions share, which is banned). This is the gate that cannot be skipped.
#
# Two checks:
#   1. Any tracked blob larger than SIZE_LIMIT_KB that is not an LFS pointer and not
#      allowlisted → fail. Catches big files on paths .gitattributes never anticipated.
#   2. Any tracked file whose attributes say `filter: lfs` but whose blob is not a pointer
#      → fail. Catches the added-before-the-rule / skipped-hook cases at ANY size.
#
# Usage:
#   .ci/run.sh lfs-guard
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

SIZE_LIMIT_KB=512

# Lockfiles are large, text, machine-merged, and belong in plain git.
ALLOWLIST=(
  "uv.lock"
  "experimental/orchestration/dagster_ogip/uv.lock"
)

is_allowlisted() {
  local path="$1" allowed
  for allowed in "${ALLOWLIST[@]}"; do
    [[ "$path" == "$allowed" ]] && return 0
  done
  return 1
}

# An LFS pointer blob is ~130 bytes and starts with this exact line.
is_lfs_pointer() {
  local path="$1"
  git cat-file blob ":${path}" 2>/dev/null | head -c 42 | grep -q '^version https://git-lfs'
}

fail=0

# ── Check 1: oversized raw blobs anywhere ────────────────────────────────────
# Sizes come from ONE `git cat-file --batch-check` over the index (an xargs-per-file
# pipeline hit ARG_MAX on this repo and silently dropped files — a guard that skips
# entries passes builds it must fail). An LFS pointer blob is ~130 bytes, so anything
# over the limit is by definition a raw blob; no per-file pointer probe needed.
index="$(git ls-files -s | awk -F'\t' '{split($1, meta, " "); print meta[2] "\t" $2}')"
while IFS=$'\t' read -r size path; do
  is_allowlisted "$path" && continue
  log "✗ ${path} is $((size / 1024))KB raw in git (limit ${SIZE_LIMIT_KB}KB) — track it: git lfs migrate import --include='${path}'"
  fail=1
done < <(
  paste \
    <(cut -f1 <<<"$index" | git cat-file --batch-check='%(objectsize)') \
    <(cut -f2- <<<"$index") |
    awk -F'\t' -v lim_bytes="$((SIZE_LIMIT_KB * 1024))" '$1 > lim_bytes'
)

# ── Check 2: LFS-attributed paths that are still raw blobs ───────────────────
while IFS= read -r path; do
  if ! is_lfs_pointer "$path"; then
    log "✗ ${path} matches an LFS pattern in .gitattributes but is a raw blob — re-add it after 'git lfs install --local'"
    fail=1
  fi
done < <(
  # No -z / NUL framing: BSD awk on macOS cannot take NUL as RS and silently emits
  # nothing — which made this check pass on a staged raw blob. Line format is
  # "<path>: filter: lfs"; repo policy keeps paths colon-free, so the suffix match is safe.
  git ls-files |
    git check-attr --stdin filter |
    sed -n 's/: filter: lfs$//p'
)

if ((fail)); then
  log "large-dataset rule: binary fixtures/samples go through Git LFS (see .gitattributes)"
  exit 1
fi
log "✓ lfs-guard: no oversized raw blobs, no broken LFS attributes"
