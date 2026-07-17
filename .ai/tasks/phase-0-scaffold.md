# Task — Phase 0: Scaffold & identity

**Status:** ✅ done — `make check` green (ruff · pyright strict 0 errors · 6 tests), `uv sync` OK.

## Delivered

- `git init` (main); `pyproject.toml` (`ogip`, py3.13, uv; deps dlt/sqlmesh/prefect/duckdb/
  pyarrow/psycopg; groups dev[+jupyterlab], ingestr, engines, dagster); ruff/pyright/sqlfluff/pytest config.
- Typed core `src/ogip/{__init__,config,logger}.py` + `py.typed` (ported from OGAP `ogap`→`ogip`).
- Config SSoT `config/config.yml` + `.env-render.py` (merge-safe secrets) + `.pre-commit-config.yaml`
  (prek) + `.yamllint.yaml`.
- Build files `Makefile` + `Justfile` (root-lean); `.gitignore`, `.python-version`, `LICENSE`, `README.md`.
- CI: `.ci/run.sh` + steps (lint · typecheck · test · sql-lint · bash-lint · structure-validate ·
  secret-scan) + `.github/workflows/ci.yml`.
- Tests: `src/tests/{smoke,unit}` (tiers smoke/unit/integration/e2e).
- `.ai/` symlinks (memory·skills gitignored; specs→../spec, scripts→../src/scripts tracked);
  root `AGENTS.md` + `.claude/CLAUDE.md` symlinks.
- Dir stubs + READMEs: ingestion/ transform/ pipelines/ dq/ spec/ src/scripts/ config/ .ci/ src/tests/.

## Decisions locked this phase

- **D15** commit + push after every successful run (green gate/pipeline).
- **D16** pre-commit via **prek** (fast, drop-in) — lint ALL (Python·SQL·Bash·YAML) + smoke tests
  on commit, data tests on pre-push, gitleaks secret scan.
- **D17** test tiers smoke / unit / integration / **e2e = run Prefect job + assert results**.
- **D18** root-lean: configs→`config/`, tests→`src/tests/`, scripts→`src/scripts/`, CI→`.ci/`;
  `structure-validate` guard enforces it.
- **D19** `.ai/` symlinks for plans/memory/skills (memory·skills gitignored; specs·scripts tracked).

## Deferred (do LATER)

- **D20** Upsert the code + project-scaffold standards established here into
  `~/.ai/skills/.settings/code_specs/` (python_module_layout · script_standards · justfile_standards)
  — the root-lean layout, prek pre-commit set, test tiers, commit+push loop, `.ai/` symlink convention.

## Next → M0 (walking skeleton)

RAWG → raw Parquet → 1st ODCS contract + Bruin SQL → SQLMesh (stg→core→mart/fs) → 1 ML parquet →
notebook + Evidence, on a Prefect flow (dlt). Then `make up` (Docker) + Prefect job green.
