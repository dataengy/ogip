#!/usr/bin/env bash
# Full-history leak scan. gitleaks in CI; no-op locally if not installed.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

if command -v gitleaks >/dev/null 2>&1; then
  log "gitleaks (full history)"
  gitleaks detect --no-banner --redact
else
  log "gitleaks not installed — skip (runs in CI; pre-commit also scans staged changes)"
fi
