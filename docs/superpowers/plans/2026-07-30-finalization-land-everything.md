# Finalization — land everything, three green run commands, dev→main (2026-07-30)

Driver: bring the repo to a showable, releasable state fast. Umbrella task:
[.ai/tasks/finalization.md](../../../.ai/tasks/finalization.md). Mode: **AUTO** (owner
directive) — phases run without per-phase approval gates; checkpoints are reported after
B/C/D, not awaited. Safety rails unchanged: never force-push `dev`/`main`; never commit a
neighbour lane's files; branch deletions only after containment proof; escape hatches on the
two risky landings stand.

## Goal state ("ready")

1. Three green commands on sample data: `make run-dbt`, `make run-bruin`,
   `make run-dagster-dbt` (Prefect + dbt-under-Dagster — already implemented as profile
   `prefect-over-dagster`; needs an alias + verified run).
2. Re-root ([#40](https://github.com/dataengy/ogip/issues/40)) T4–T9 finished: dbt+bruin
   primary in config/Makefile/gates/AGENTS.md + ADR-0020.
3. Every lane landed or loudly frozen: dagster [#34](https://github.com/dataengy/ogip/pull/34),
   odos [#37](https://github.com/dataengy/ogip/issues/37); placeholder branches deleted.
4. DQ monitors either execute (non-zero on failure) or are loudly deferred — no silent green.
5. `dev → main` PR [#10](https://github.com/dataengy/ogip/pull/10) merged, CI green.
6. Showcase deck (external deck-generator repo) + outreach drafts — content off-repo.

Tiers: **V1** pitch-minimum (A, B, E) ≈ 1.5–2 d · **V3** += C (re-root landed) ·
**V4** += D (everything landed, main releasable) · **V2** = V4 + real DQ schedule + all
sources + live R2 + real VPS deploy (not required for the showcase).

## DAG (S<2h · M 2–6h · L>6h)

**A — ground clearing** ·
1 [S] safety-push `lane/odos-compiler` (was the only copy), verify, then `git worktree prune`.
2 [S] break 3 stale locks (obj--airbyte; obj--core-pipeline + obj--dagster in worktree-local
stores) + sweep dangling `~/.ai/.locks` symlinks.
3 [S] restore corrupted `pipelines/dbt/prefect.yaml` (diff snapshot → `git checkout -- <path>`).
4 [S] neighbour dirty files (root `.gitignore`, `spec/ODTS/examples/*`,
`src/tests/unit/test_standard_packages.py`) stay untouched; fallback before step 22:
`lane/neighbour-salvage` with authorship note. `.ai/CONTEXT.man.md` → `.git/info/exclude`.
5 [S] reconcile local `dev` (rebase onto origin/dev in a throwaway worktree).

**A0 — planning/tasking docs upsert** (this document, STATUS, umbrella task,
techdebt register, ROADMAP/FIXME/CHANGELOG annotations, `.cache/` gitignore fix, tasks-sync,
issue triage: close #28 and verify-close #30/#31).

**B — three commands green** ·
6 [S] merge origin/dev → reroot lane; `make check`.
7 [S-M] `make run-dbt` E2E green (exit 0 + row count).
8 [S] `make run-bruin` E2E green.
9 [M] `run-dagster-dbt` alias → `run-over-dagster`; `uv sync` in
`experimental/orchestration/dagster_ogip`; verify `_DLT_ASSET`/`_DBT_SUBGRAPH` selections;
E2E run. Do NOT build a dagster-as-orchestrator path. Re-verify after #34.
10 [S] `dq/run.py`: WARNING banner "monitors defined but NOT EXECUTED — deferred", techdebt
row; stays out of `make check` until step 19.

**C — re-root T4–T9 (Refs #40)** ·
11 [S] T4: `config/config.yml` default → `prefect-dbt`, `experimental: true` on demoted
profiles; `Makefile` `run: run-dbt`; EXPERIMENTAL banner in `src/scripts/run-profile.py`.
12 [M] T6 (CI risk pivot): `test_all_setups.py` BASE_ENGINES=["dbt","bruin"], rest behind
`OGIP_E2E_ALL_ENGINES=1`; `test_wiring.py` expects dbt; assert `name`+`prefect-version` in
every `prefect.yaml` (the corruption in step 3 was invisible to the old assert). Full
`make check` + 8 CI jobs green on the lane before merge.
13 [M] T5: `.ai/AGENTS.md` hard rules 1–2 rewrite (dbt+bruin primary, SQLMesh experimental)
+ ADR-0020, consistent with ADR-0016 → closes FIXME F1.
14 [S-M] T7: regenerate snapshots; fix `pipelines/README.md`, `spec/ODOS/IMPLEMENTATION.md`
(+F8 ODPS→YADPS), `spec/ODTS/IMPLEMENTATION.md`. T9: materialize
`src/scripts/preflight-clean-ground.sh` + `gh-merge-as.sh` + Justfile recipes. T8 = skipped
by design (recorded here).
15 [S] PR reroot → dev, merge on 8/8 green. Re-root lands BEFORE #34: it is near-sync and
trunk-defining; the reverse order would rewrite T4–T9 against a moving base.

**D — land the rest** ·
16 [L] #34 catch-up: merge origin/dev (incl. re-root) in the dagster worktree. Conflict
hotspots: dbt-path SSoT vs T4/T7, `.ai/` docs, `pipelines/_shared/`, dagster_ogip defs vs
step-9 asset keys. Gates: main CI + `dagster-e2e.yml` + re-run `make run-dagster-dbt`. Merge.
17 [M] odos: merge dev (post-#34; hotspot: odos_runtime bridge vs flattened defs), PR
Refs #37, merge. Escape hatch: if bridge rework >2h → freeze (branch stays pushed, #37
labelled TBD + techdebt row).
18 [S] delete branches+worktrees after containment proof (`git branch --merged origin/dev`):
core-pipeline, transform-dq-expansion, airbyte, evidence/obs/s3/vps; dagster after 16.
19 [M] DQ minimum: declared monitors (row_count/not_null) actually execute against duckdb
outputs, non-zero on failure, wired into `make check` + CI; seeded failure proves non-zero.
20 [M] TBD-disable sweep (register: [docs/techdebt/finalization-tbd.md](../../techdebt/finalization-tbd.md))
+ issue triage (#19 body via targeted sync; #8 stale marker; #39 if <30 min; relabel
#13/#11/#23/#33/#26/#9).
21 [M] docs refresh: `.ai/STATUS.md` full rewrite, ROADMAP post-re-root, FIXME closures
(F1@13, F8@14, F2 cheap sweep, F4 stub-READMEs), commit `spec/ODTS/proposals/` with its
pre-normative banner (Refs #35/#36/#20).
22 [M] dev→main: refresh PR #10 body; pre-checks: branch-protection required-check names
match workflow jobs; no `.venv` tracked under `experimental/orchestration/dagster_ogip/`;
neighbour work committed (step 4 deadline). Merge. Never force-push.

**E — showcase (off-repo)** ·
23 [M] deck via the deck-generator repo (story: one platform — three interchangeable engine
setups — green runs as evidence). 24 [S] two outreach drafts building on the deck; kept
off-repo.

## Risks (top-5)

1. #34 catch-up blast radius (76 behind + re-root) → single resolution session in the
   dagster worktree; dbt-path SSoT first; V1/V3 do not depend on it.
2. T6 e2e flip breaks CI → steps 7–8 green locally first; flip + fixture fixes in one PR;
   `OGIP_E2E_ALL_ENGINES` escape hatch.
3. Shared-checkout neighbour drift → only surgical main-checkout action was step 3 (one
   file, snapshotted); everything else in worktrees; salvage-branch fallback.
4. dev→main 140-commit PR surprises → step-22 pre-checks; CI exercised on dev by 15–17.
5. odos loss (was unpushed) → closed by step 1 on day 0.

## Execution log

- 2026-07-30 · **A done**: odos pushed (`0a05a8e` on origin) → stub worktree pruned;
  3 stale locks broken + 85 dangling lock symlinks removed; `pipelines/dbt/prefect.yaml`
  restored (`name: ogip-dbt`, `prefect-version: 3.0.0` — corruption diff snapshotted to
  scratchpad); `.ai/CONTEXT.man.md` excluded locally; local `dev` rebased — all 3 local
  commits were already contained in origin/dev, `dev == origin/dev`, nothing pushed.
- 2026-07-30 · **A0 done**: this plan + umbrella #43 + run-dagster-dbt #44 + techdebt register;
  tasks-sync realigned #18/#19 bodies (F6 fixed); closed #28/#30/#31; STATUS/ROADMAP/FIXME/
  CHANGELOG annotated. Neighbour work salvaged AND finished on `lane/neighbour-salvage` →
  PR #45 merged to dev (fixture-contract test + all 6 fixtures at parity + ru-gitignore).
- 2026-07-30 · **B done — three commands green** on sample data, each exit 0 with outputs
  `{games:5, market_features:5, ml_train:5}`: `make run-dbt` (dbt build PASS=157 ERROR=0) ·
  `make run-bruin` · `make run-dagster-dbt` (new alias → prefect-over-dagster). Defects found
  and fixed on the way: **(1)** runtime dbt regen leaked this machine's absolute path into the
  5 tracked raw models (never committed; generator now renders portable `./.run/…`);
  **(2)** bruin's connection path resolves against `.bruin.yml`, not CWD — emitted
  project-relative now (was: every asset failed "cannot open database");
  **(3)** the Prefect+Dagster seam never regenerated the dagster dbt render — stale
  profiles.yml with a relative path died inside Dagster's staged copy; the flow now mirrors
  run_combo.sh (absolute paths into the UNTRACKED render). DQ loud-stub shipped (step 10).
- 2026-07-30 · **C in flight**: T4 (config default→prefect-dbt + experimental flags + banner,
  `make run`→run-dbt) · T5 (ADR-0020 + AGENTS.md engine clauses; F1 deliberately left open —
  it moves with #35) · T6 (BASE_ENGINES=[dbt,bruin]; test_wiring→dbt; prefect.yaml
  name/version asserts; **CI e2e job now installs the Bruin CLI**) · T7 (pipelines/README,
  ODOS/ODTS IMPLEMENTATION, ADR index 0017–0020 backfilled; F8 verified gone → row deleted) ·
  T8 skipped by design · T9 (`preflight-clean-ground.sh` + `gh-merge-as.sh` + `just preflight`
  / `just gh-merge-as`; live self-test ran). Next: full gate → PR reroot→dev (step 15).
- Discovered for step 22: PR #10's failing check is **combo-e2e** (dagster-e2e workflow) —
  investigate before the dev→main merge.
