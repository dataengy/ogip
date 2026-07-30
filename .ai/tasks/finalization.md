# Task — Finalization: land everything, three green run commands, dev→main

**Status:** 🚧 in progress (started 2026-07-30) · **Priority:** **P1** ·
**Issue:** [#43](https://github.com/dataengy/ogip/issues/43)

Umbrella over the finalization run; the plan of record is
[docs/superpowers/plans/2026-07-30-finalization-land-everything.md](../../docs/superpowers/plans/2026-07-30-finalization-land-everything.md).
Mode: AUTO (owner directive) — no per-phase approval gates; checkpoint reports after B/C/D.

## Goal ("ready")

- `make run-dbt` · `make run-bruin` · `make run-dagster-dbt` — all green E2E on sample data.
- Re-root T4–T9 done (#40): dbt+bruin primary in config, Makefile, gates, AGENTS.md; ADR-0020.
- Lanes landed or loudly frozen: dagster PR #34, odos #37; placeholder branches deleted.
- DQ monitors execute (non-zero on failure) — or are loudly deferred, never silently green.
- dev → main PR #10 merged, CI green, main releasable.
- Showcase deck (external deck-generator repo) + outreach drafts — content stays off-repo.

## Checklist (phases)

- [x] **A** — ground clearing: odos safety-push · 3 stale locks broken · corrupted
      `pipelines/dbt/prefect.yaml` restored · local `dev` reconciled (== origin/dev)
- [ ] **A0** — planning/tasking docs upsert + tasks-sync + issue triage (this commit)
- [ ] **B** — three green run commands + DQ loud-stub
- [ ] **C** — re-root T4–T9 + reroot→dev PR (Refs #40)
- [ ] **D** — land #34/#37 · delete 7 branches+worktrees · DQ-minimum · TBD sweep ·
      docs refresh · dev→main (#10)
- [ ] **E** — showcase deck + outreach drafts (off-repo)

## Acceptance

- CI green on `dev` and `main`; only `main`/`dev` + genuinely active lanes remain in
  `git branch -a`; STATUS/ROADMAP/techdebt ≤1 day stale; every deferred feature has a loud
  stub + a row in [docs/techdebt/finalization-tbd.md](../../docs/techdebt/finalization-tbd.md)
  + an issue.
