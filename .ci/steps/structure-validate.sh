#!/usr/bin/env bash
# Root-lean guard: fail if a stray FILE lands in the repo root. Config → config/,
# tests → src/tests/, scripts → src/scripts/, CI → .ci/, docs → docs/, AI → .ai/.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

allowed=(
  pyproject.toml uv.lock README.md LICENSE Makefile Justfile
  .gitignore .python-version .env AGENTS.md
)
is_allowed() {
  local f="$1"
  for a in "${allowed[@]}"; do [[ "$f" == "$a" ]] && return 0; done
  return 1
}

stray=()
while IFS= read -r f; do
  f="${f#./}"
  is_allowed "$f" || stray+=("$f")
done < <(find . -maxdepth 1 -type f ! -name '.*' -o -maxdepth 1 -type l | sed 's|^\./||')

# Allow the AGENTS.md symlink; flag any other stray root file.
real_stray=()
for f in "${stray[@]}"; do [[ "$f" == "AGENTS.md" ]] || real_stray+=("$f"); done

if [[ ${#real_stray[@]} -gt 0 ]]; then
  log "stray files in root (move them into config/ · src/ · .ci/ · docs/ · .ai/):"
  printf '  - %s\n' "${real_stray[@]}"
  exit 1
fi
log "root is lean — OK"
