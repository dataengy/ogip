# Task — Session coordination: lanes, ship loop, task-bound commits, PR flow

**Status:** 🟡 in progress — lane locking + ship loop + commit binding shipped; worktrees proposed.

## Why

Six agent sessions (core-pipeline · obs · evidence · dagster · s3 · vps) work the **same
checkout**. Without mechanics, sessions sweep each other's files into commits, break each
other's gates, and duplicate work. Two real incidents already happened:

- **Duplicate tracker**: two sessions independently built a tasks-sync; markers differed by a
  single space (`ogip-task:<slug>` vs `ogip-task: <slug>`) → duplicate issues #4–#7 (deleted).
  Converged on `src/scripts/tasks_sync.py`.
- **Cross-lane gate breakage**: an in-flight `src/ogip/storage.py` from the S3 lane turned
  `make check` red and blocked an unrelated lane's ship.

## Delivered

- `src/scripts/lane.sh` — `settle` (fetch · drift · dirty · lock inventory) + `acquire`/`check`/
  `release`, delegating to the global `agent-session-lock.sh` primitive (no new lock logic).
- `src/scripts/ship.sh` — `lane guard → settle → make check → scoped commit → push → watch CI →
  tasks-sync → tg-inform`. Never `git add -A`; stages the lane allowlist and **unstages contested
  SSoT files** (pyproject/Justfile/config.yml/STATUS.md) unless this session holds their lock.
- `src/scripts/check-commit-msg.sh` + prek `commit-msg` hook — **every commit must reference an
  issue** (`Refs: #N`). Comment-aware (a bare `#12` line is a git comment, not a binding);
  merge/revert/fixup exempt.
- Branch flow: work on **`dev`**, PR → `main`. CI runs on pushes to `main`/`dev` and on PRs.

## Verified

- `lane settle` lists live locks + drift; lock acquire/check round-trips.
- commit-msg hook: rejects unbound, accepts `Refs: #N`, rejects a comment-only `#12`, exempts merges.
- All 4 task files carry issues (#1 #2 #3 #8) via `just tasks-sync`.

## Open / proposed

- **git worktrees per session** (strong recommendation): one checkout+branch per lane removes
  shared-tree hazards structurally — no cross-lane gate breakage, no `add -A` risk, no contested
  staging. Locks would then guard only merges.
- Upstream bug: `/agent-session-lock`'s `just agent-lock` recipe re-parses `--reason` via
  `bash -c`, so parentheses crash it; the direct script is fine.
- **D20**: upsert these scaffold standards into `~/.ai/skills/.settings/code_specs/`.
- Disk pressure: 6 sessions × uv envs on a ~13G volume hit ENOSPC once (uv cache 1.3G).
