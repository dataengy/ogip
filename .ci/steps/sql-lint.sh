#!/usr/bin/env bash
# Lint portable SQL under spec/sql. Bruin `@bruin ... @bruin` YAML headers are valid SQL
# block comments, so sqlfluff parses the statement after them; no stripping needed.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

mapfile -t sql_files < <(find spec/sql -type f -name '*.sql' 2>/dev/null || true)
if [[ ${#sql_files[@]} -eq 0 ]]; then
  log "no SQL under spec/sql yet — skip"
  exit 0
fi
log "sqlfluff lint (${#sql_files[@]} files)"
uv run sqlfluff lint "${sql_files[@]}"
