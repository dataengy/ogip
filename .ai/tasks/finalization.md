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
- [x] **A0** — planning/tasking docs upsert + tasks-sync + issue triage (#43/#44 created;
      #28/#30/#31 closed; F6 fixed; neighbour work salvaged+finished → PR #45 merged)
- [x] **B** — three green run commands (`run-dbt` · `run-bruin` · `run-dagster-dbt`, all
      exit 0, outputs 5/5/5) + DQ loud-stub; 3 latent path bugs fixed (dbt/bruin/dagster)
- [x] **C** — re-root T4–T9 done, PR #46 merged (T8 skipped by design; ADR-0020; #40 closed)
- [ ] **D** — in flight: ✓ retired branches marked stale (kept — owner directive; worktree dirs of retired lanes removed) · ✓ DQ executor (PR #47, day-one
      catch: empty console_pricing → demo coherent) · ✓ TBD sweep + issue triage (#39/#40/#44
      closed, 6 frozen issues carry techdebt pointers) · ✓ docs refresh · remaining: dagster
      #34 (agent), odos #37, dev→main (#10)
- [~] **E** — deck BUILT & validated (31 slides, deck-factory repo, pptx+html in ~/Downloads);
      outreach drafts written to `.ai/outreach-drafts.local.md` (excluded) — merge with the TG
      thread's base drafts manually

## Acceptance

- CI green on `dev` and `main`; every non-active branch is listed in
  [docs/techdebt/stale-branches.md](../../docs/techdebt/stale-branches.md) (kept, marked —
  never deleted); STATUS/ROADMAP/techdebt ≤1 day stale; every deferred feature has a loud
  stub + a row in [docs/techdebt/finalization-tbd.md](../../docs/techdebt/finalization-tbd.md)
  + an issue.
