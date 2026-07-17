# OGIP — Project Instructions (Claude Code)

**OGIP (Open Games Intelligence Platform)** — production-grade OSS **Market Intelligence
Platform** for the games industry; product = **ML-ready Parquet datasets** for DS/ML/Analysts.
Portfolio-quality showcase for Senior/Staff Data Engineer skills. Successor to OGAP
(`../Hushcrasher/`), intentionally simpler.

**Primary rules live in [AGENTS.md](AGENTS.md)** (same directory) — general rules, the
"production path is sacred" principle, layer naming law, `spec/` SSoT (Bruin + ODCS),
SSoT config, quality bar, run profiles. This file adds Claude-specific workflow notes only.

## Workflow

- Phased delivery with **user approval gates** after each phase
  (plan: [PLAN.md](PLAN.md) · status: [STATUS.md](STATUS.md) · tasks: [tasks/](tasks/)).
- After each phase: explain decisions, show the tree, ask approval before continuing.
- Batch/one-off work goes through scripts in `.tmp/` (`.tmp/.once/` for one-shots);
  durable interfaces go to Makefile/Justfile + docs.
- Commits via /smart-commit conventions: Conventional Commits, split by category
  (chore(ai)/docs/ci/feat/test), no push without asking.

## Commands (target — created during Phase 0)

- Gates: `make check` (= ruff + pyright strict + pytest); CI parity: `make ci`
- Run: `make run` (full pipeline on sample data); `just run-profile <name>` (A12 profiles)
- Infra: `make up` / `make obs-up` / `make down` (compose: `deploy/docker-compose.yml`, env: rendered `.env`)
- Config: edit `config/config.yml` → `make render-env` (never edit derived `.env` values)
- Runtime env: `UV_PROJECT_ENVIRONMENT=.run/venv` (exported by all build files)

## Key paths

`src/ogip/` (package) · `ingestion/` (base/common/sources) · `spec/` (SSoT: contracts + Bruin SQL) ·
`transform/` (SQL runner) · `dq/` · `pipelines/` (Prefect) · `outputs/`+`examples/` ·
`experimental/` (engines/orchestration/semantic/bi — off prod path) · `deploy/` · `config/` ·
`docs/` · `.run/` (runtime, gitignored).
