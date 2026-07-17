#!/usr/bin/env bash
# Lint + format-check all Bash under tracked script dirs.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

mapfile -t sh_files < <(find .ci config deploy src/scripts -type f -name '*.sh' 2>/dev/null || true)
if [[ ${#sh_files[@]} -eq 0 ]]; then
  log "no shell scripts found — skip"
  exit 0
fi
if command -v shellcheck >/dev/null 2>&1; then
  log "shellcheck (${#sh_files[@]} files)"
  # SC1091: can't follow the dynamic `source .../_common.sh` — expected, not a defect.
  shellcheck -e SC1091 "${sh_files[@]}"
else
  log "shellcheck not installed — skip (runs in pre-commit/CI image)"
fi
if command -v shfmt >/dev/null 2>&1; then
  log "shfmt -d"
  shfmt -i 2 -ci -d "${sh_files[@]}"
else
  log "shfmt not installed — skip"
fi
