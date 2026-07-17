# `.ci/` — shared CI step library

`run.sh <step>` is the single entry point; GitHub Actions (`.github/workflows/ci.yml`) is a
thin frontend that calls it, so pipelines stay reproducible and runnable locally (`make ci`).

| Step | Does |
|---|---|
| `lint` | ruff check + format + SQL lint (`sql-lint`) |
| `typecheck` | pyright strict |
| `test` | pytest smoke + unit (junit artifact) |
| `bash-lint` | shellcheck + shfmt over tracked `*.sh` |
| `structure-validate` | root-lean guard (no stray files in the repo root) |
| `secret-scan` | gitleaks (full history) |
