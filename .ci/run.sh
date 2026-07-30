#!/usr/bin/env bash
# Single CI entry point — GitHub Actions calls ONLY this script.
# Usage: .ci/run.sh <step>   (steps live in .ci/steps/<step>.sh)
set -euo pipefail

step="${1:?usage: .ci/run.sh <lint|typecheck|test|sql-lint|bash-lint|structure-validate|secret-scan|lfs-guard>}"
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
script="${dir}/steps/${step}.sh"

[[ -f "${script}" ]] || {
  echo "[ci] unknown step: ${step}" >&2
  exit 2
}
exec bash "${script}"
