#!/usr/bin/env bash
# public-hygiene.sh — refuse to publish another organisation's identifiers.
#
# OGIP is a PUBLIC repo whose architecture is informed by work done in a private corporate
# one. gitleaks (.ci/steps/secret-scan.sh) covers half of a leak: secrets — tokens, keys,
# passwords. This covers the other half: identifiers that are not secret, and still are not
# ours to publish — tracker ids, internal hostnames, private checkout paths, bot names.
#
# Why a gate and not a habit: this repo's clean-room port of a private alerting stack WAS
# hand-checked with exactly this grep, and a corporate path still reached a public commit —
# in an agent file nobody thought to re-check. A rule that lives in a head is a rule that
# holds until the day it matters.
#
# Scans TRACKED files in the working tree. gitleaks already walks history; this is about not
# adding to it — history on a shared branch cannot be rewritten (several agent sessions commit
# to it), so a marker that lands is a marker that stays.
#
# Usage:
#   bash src/scripts/public-hygiene.sh            # scan; exit 1 on any finding
#   bash src/scripts/public-hygiene.sh --list     # print the markers, scan nothing
#
# Exit codes: 0 clean · 1 markers found · 2 bad usage
#
# The marker list is literal and lives here rather than in config/config.yml because config/
# belongs to the core-pipeline lane; folding it into the SSoT is a handoff (.ai/STATUS.md).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

SELF_REL="src/scripts/public-hygiene.sh" # this file spells out every marker; never scan it

log() { echo "[hygiene] $*"; }
die() {
  echo "[hygiene] ERROR: $*" >&2
  exit 2
}

# Parallel arrays, not one delimited string: the patterns contain `|` themselves, and not one
# associative array — macOS still ships bash 3.2. Index i means the same marker in all three.
MARKER_LABELS=(
  "corporate tracker id"
  "private checkout path"
  "internal hostname"
  "organisation name"
  "bot / product name"
)
MARKER_DESCS=(
  "an issue key from a private tracker"
  "a path into the private stack"
  "an internal service host"
  "the private organisation's name"
  "a bot from the private stack"
)
# ERE for `git grep -E`. No \b — that is a GNU extension and git's matcher is not GNU's.
MARKER_PATTERNS=(
  '(ANALYTICS|DEVOPSN|LABA)-[0-9]+'
  'pdp[._-]deploy_dev|dagster_pdp'
  'jira\.tasktracker\.help|gibus\.[a-z0-9.-]+'
  'prodamus'
  'PDP[[:space:]]+Bot'
)

case "${1:-}" in
  --list)
    for i in "${!MARKER_LABELS[@]}"; do
      printf '  %-22s %s\n' "${MARKER_LABELS[$i]}" "${MARKER_DESCS[$i]}"
    done
    exit 0
    ;;
  -h | --help)
    sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  "") ;;
  *) die "unknown arg: $1 (try --help)" ;;
esac

command -v git >/dev/null 2>&1 || die "git not found"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not a git work tree: $REPO_ROOT"

found=0
for i in "${!MARKER_LABELS[@]}"; do
  # -I skips binaries. The pathspec excludes this file, which names every marker by design.
  # git grep exits 1 when nothing matches — that is the clean case, not an error.
  if hits="$(git grep -nIE "${MARKER_PATTERNS[$i]}" -- . ":(exclude)${SELF_REL}" 2>/dev/null)"; then
    found=1
    log "FOUND — ${MARKER_LABELS[$i]} (${MARKER_DESCS[$i]}):"
    printf '%s\n' "$hits" | sed 's/^/    /' >&2
  fi
done

if [[ "$found" -eq 1 ]]; then
  echo >&2
  echo "  This is a PUBLIC repo. The lines above name a private organisation's tickets, hosts," >&2
  echo "  paths or bots. Architecture may be reused; identifiers may not." >&2
  echo "  Rewrite the line generically ('a private monitoring stack') rather than deleting it —" >&2
  echo "  the next reader still needs to know where the design came from." >&2
  exit 1
fi

log "clean — no corporate markers in ${REPO_ROOT##*/} (tracked files)"
