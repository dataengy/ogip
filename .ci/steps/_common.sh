#!/usr/bin/env bash
# Shared helpers for CI steps. Source at the top of each step.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Runtime env lives under .run/ — keep CI, Makefile, and pyright (venvPath=.run) in agreement.
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-.run/venv}"

log() { echo "[ci] $*"; }
