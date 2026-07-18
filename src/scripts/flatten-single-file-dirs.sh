#!/usr/bin/env bash
# flatten-single-file-dirs.sh — collapse "directory holding exactly one module" into one file.
#
# A package directory earns its keep when it holds several modules or a real __init__ API.
# When it holds a single file, the directory is pure indirection: deeper paths, an extra
# __init__, and a name repeated twice (foo/definitions.py). This flattens that shape:
#
#     <dir>/<inner>.py   ->   <dir>.py          (default inner name: the dir's only *.py)
#
# SAFE BY DEFAULT: dry-run unless --apply is passed. Refuses to touch a directory that
# would lose information — more than one module, a non-trivial __init__.py, or any file
# still referenced by path/import elsewhere in the repo (checked with grep, reported not
# guessed). `git mv` is used so history follows the file.
#
# Usage:
#   flatten-single-file-dirs.sh <parent-dir> [...]              # dry-run report
#   flatten-single-file-dirs.sh --apply <parent-dir> [...]      # perform the moves
#   flatten-single-file-dirs.sh --inner definitions.py <dir>    # only this inner filename
#   flatten-single-file-dirs.sh --skip warehouse <dir>          # leave a child alone (repeatable)
#
# Exit: 0 ok (or nothing to do) · 1 a candidate was refused · 4 bad usage.
set -euo pipefail

APPLY=0 INNER="" SKIPS=() PARENTS=()

log() { echo "[flatten] $*"; }
die() {
  echo "[flatten] ERROR: $*" >&2
  exit 4
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --inner)
      INNER="${2:?--inner needs a filename}"
      shift 2
      ;;
    --skip)
      SKIPS+=("${2:?--skip needs a name}")
      shift 2
      ;;
    -h | --help)
      sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    -*) die "unknown flag: $1" ;;
    *)
      PARENTS+=("$1")
      shift
      ;;
  esac
done

[[ ${#PARENTS[@]} -gt 0 ]] || die "need at least one parent dir (try --help)"

REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git work tree"
refused=0 moved=0

is_skipped() {
  local name="$1" s
  for s in ${SKIPS[@]+"${SKIPS[@]}"}; do [[ "$s" == "$name" ]] && return 0; done
  return 1
}

# A trivial __init__.py (absent, empty, or only comments/docstring) carries no API to lose.
init_is_trivial() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  ! grep -qvE '^\s*(#.*)?$' "$f"
}

for parent in "${PARENTS[@]}"; do
  [[ -d "$parent" ]] || die "not a directory: $parent"
  for dir in "$parent"/*/; do
    [[ -d "$dir" ]] || continue
    name="$(basename "$dir")"
    [[ "$name" == __pycache__ || "$name" == .* ]] && continue
    is_skipped "$name" && {
      log "SKIP $name (--skip)"
      continue
    }

    rm -rf "${dir}__pycache__"
    mapfile -t mods < <(find "$dir" -maxdepth 1 -name '*.py' ! -name '__init__.py' -print | sort)

    if [[ ${#mods[@]} -ne 1 ]]; then
      log "skip $name — holds ${#mods[@]} modules, the directory is earning its keep"
      continue
    fi
    src="${mods[0]}"
    [[ -z "$INNER" || "$(basename "$src")" == "$INNER" ]] || {
      log "skip $name — inner is $(basename "$src"), not $INNER"
      continue
    }

    if ! init_is_trivial "$dir/__init__.py"; then
      log "REFUSE $name — __init__.py has real content (would be lost)"
      refused=1
      continue
    fi

    # Anything importing `<parent>.<name>` or the file's path breaks on a flatten. Report it.
    pkg_path="${dir#"$REPO"/}"
    if grep -rqE "$(basename "$parent")[./]${name}[./]" "$REPO" \
      --include='*.py' --include='*.sh' --include='*.yaml' --include='*.yml' --include='*.toml' \
      --exclude-dir=.venv --exclude-dir=__pycache__ --exclude-dir=.git 2>/dev/null; then
      log "REFUSE $name — still referenced by path/import elsewhere:"
      grep -rnE "$(basename "$parent")[./]${name}[./]" "$REPO" \
        --include='*.py' --include='*.sh' --include='*.yaml' --include='*.yml' --include='*.toml' \
        --exclude-dir=.venv --exclude-dir=__pycache__ --exclude-dir=.git 2>/dev/null | sed 's/^/    /' | head -5
      refused=1
      continue
    fi

    dest="${dir%/}.py"
    [[ -e "$dest" ]] && {
      log "REFUSE $name — $dest already exists"
      refused=1
      continue
    }

    if [[ "$APPLY" -eq 1 ]]; then
      git mv "$src" "$dest"
      if [[ -f "$dir/__init__.py" ]]; then
        git rm -q --cached "$dir/__init__.py" 2>/dev/null || true
        rm -f "$dir/__init__.py"
      fi
      rmdir "$dir"
      log "flattened ${pkg_path}$(basename "$src") -> ${dest#"$REPO"/}"
    else
      log "would flatten ${pkg_path}$(basename "$src") -> ${dest#"$REPO"/}"
    fi
    moved=$((moved + 1))
  done
done

if [[ "$APPLY" -eq 0 && "$moved" -gt 0 ]]; then
  log "dry-run — re-run with --apply to perform the $moved move(s)"
fi
[[ "$refused" -eq 0 ]] || log "some candidates were refused (see above) — nothing was forced"
exit "$refused"
