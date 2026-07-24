# Re-root: prefect+dbt & prefect+Bruin as Primary Candidates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make **prefect+dbt** and **prefect+Bruin** the two primary, production-grade comparison candidates; move every other engine setup (sqlmesh, plain_sql, opendbt, sqlmesh_dbt, dagster) to experimental/R&D — off the default `make`/pipeline path.

**Architecture:** OGIP authors transforms once in `spec/sql` (`@bruin` format, ODTS — no YADTS). Today the spec compiler renders that to engine projects and SQLMesh is the hard-wired production default. This re-root inverts that: dbt and Bruin become the two co-primary runtimes on the default path, exercised by `make`/CI; the rest become comparison setups under `experimental/`. Because dbt becomes primary, the dbt/Dagster combo path (#38) and dbt-native DQ (#34) become foundational, not optional.

**Tech Stack:** Python 3.13 (uv, ruff, pyright-strict, pytest), DuckDB, dbt-core + dbt-duckdb, Bruin, Prefect 3.7, SQLGlot (compiler), SQLMesh (now experimental).

## Global Constraints

- **ODTS naming is settled: `ODTS`, no `YADTS`** (ADR-0018). Do not reintroduce a YADTS variant.
- **`spec/` stays SSoT and engine-agnostic** — authored in `@bruin` SQL; engine projects are GENERATED, never hand-forked. This re-root does not change the authoring format; it changes which generated engines are primary.
- **`spec/ODTS/examples/` is a frozen 6-file normative set** — `test_standard_packages.py` asserts `==6` + body-byte-identity. Do NOT add or reformat example bodies.
- **Two co-primaries, one technical default for `make run`:** pick **prefect-dbt** as `default: true` (the single default a bare `make run` needs); **prefect-bruin** is co-primary and equally gated. Both MUST be green in `make check`.
- **Quality bar unchanged:** Ruff clean, Pyright strict 0 errors, pytest green. House `log` alias. Every new/changed directory keeps its `README.md`. Architectural change ⇒ ADR.
- **Isolated worktree + PR.** `dev` is live under parallel sessions; do the whole re-root in a worktree and land via PR. Never force-push `dev`/`main`.
- **Preconditions before Task 1:** PR #29 is merged (it conflicts on `pipelines/flows/main.py` + `pipelines/_shared/steps.py`, which this plan moves), and `dev` lint is green (via #29). Branch the worktree off post-#29 `dev`.
- Every commit ends with `Refs: #40` (or the specific sub-issue #38/#39) + `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## File Structure

**Moved (git mv, history-preserving):**
- `pipelines/{sqlmesh,plain_sql,opendbt,sqlmesh_dbt,dagster}/` → `experimental/pipelines/{...}/` — the five demoted sub-projects.
- `pipelines/{dbt,bruin}/` — STAY (the two primaries).
- `pipelines/_shared/` — STAYS (shared step lib; imported by both primary and experimental sub-projects).

**Modified:**
- `pipelines/_shared/engines.py` — `ENGINE_FLOWS` values repointed for moved engines (`experimental.pipelines.<e>.flow`).
- `pipelines/_shared/steps.py::build_warehouse` — default branch becomes dbt; sqlmesh branch still reachable for the experimental setup.
- `src/ogip/spec_compile/__init__.py` + `to_dbt.py`/`to_bruin.py`/`to_sqlmesh.py` — dbt/bruin become the default compile targets; extend check-projection for #34's dbt-native checks.
- `config/config.yml` — `run_profiles`: move `default: true` to `prefect-dbt`; relabel the five as `experimental: true`.
- `.ai/AGENTS.md` — rewrite hard rules 1–2, the production-path section, and the run-profiles section.
- `Makefile` — `run` → dbt; add `run-bruin` as co-primary; move sqlmesh/opendbt/etc targets under an `experimental-*` group.
- `src/scripts/run-profile.py` — no logic change (reads `ENGINE_FLOWS`); verify it resolves moved modules.
- Tests: `src/tests/unit/test_engine_projects_cover_spec.py`, `test_prefect_subprojects.py`, `src/tests/e2e/test_all_setups.py`.
- Snapshots: `transform/dbt/`, `transform/bruin/` stay committed + drift-guarded; `transform/sqlmesh/models/` stays gitignored.

**Created:**
- `experimental/pipelines/README.md` — what lives here and why (comparison setups, off the default path).
- `docs/adr/ADR-0020-dbt-bruin-primary-candidates.md`.
- `src/scripts/preflight-clean-ground.sh` — the pre-restructure recon (Task 9).
- `src/scripts/gh-merge-as.sh` — switch→merge→restore wrapper (Task 9).

---

## Task 1: Compiler — dbt & Bruin as default targets; accept dbt-native DQ (#34)

**Files:**
- Modify: `src/ogip/spec_compile/__init__.py`, `src/ogip/spec_compile/to_dbt.py`, `src/ogip/spec_compile/to_bruin.py`, `src/ogip/spec_compile/to_sqlmesh.py`
- Test: `src/tests/unit/test_spec_compile_dq.py` (extend), `src/tests/unit/test_reroot_default_targets.py` (create)

**Interfaces:**
- Consumes: existing `compile_to_dbt(spec_sql, out)`, `compile_to_bruin(...)`, `compile_to_sqlmesh(...)`, and the `Asset.meta` `@bruin` header (retains `columns[].checks`, top-level `checks`, and now `custom_checks`/`unit_tests`).
- Produces: `DEFAULT_ENGINES = ("dbt", "bruin")`; dbt projection emits `relationships`/`accepted_range`/`custom_checks` as dbt tests and `unit_tests` as dbt unit tests; sqlmesh projection tolerates (ignores with a logged skip) the dbt-only check kinds instead of raising `SqlSpecError`.

- [ ] **Step 1: Write the failing test** — dbt-native checks project to dbt tests, and no longer crash sqlmesh compile.

```python
# src/tests/unit/test_spec_compile_dq.py (add)
def test_dbt_native_checks_project_to_dbt_tests(tmp_path):
    from ogip.spec_compile import compile_to_dbt
    # market_features carries relationships + custom_checks + unit_tests (from #34)
    proj = compile_to_dbt(SPEC_SQL, tmp_path)
    schema = (tmp_path / "models" / "fs" / "market_features.yml").read_text()
    assert "relationships" in schema and "to: ref('game')" in schema
    # custom_checks → a singular test file; unit_tests → dbt unit_tests block
    assert (tmp_path / "tests" / "popularity_requires_ratings.sql").exists()
    assert "unit_tests:" in schema

def test_sqlmesh_ignores_dbt_only_checks_without_crashing(tmp_path):
    from ogip.spec_compile import compile_to_sqlmesh
    # relationships/custom_checks/unit_tests are dbt-only; sqlmesh must SKIP, not raise
    models = compile_to_sqlmesh(SPEC_SQL, tmp_path / "models")
    assert "fs.market_features" in models  # compiled, dbt-only checks skipped
```

- [ ] **Step 2: Run to verify it fails** — `uv run pytest src/tests/unit/test_spec_compile_dq.py -k dbt_native -q` → FAIL (relationships not emitted / sqlmesh raises).

- [ ] **Step 3: Implement** — in `to_dbt.py`, map `relationships`→dbt `relationships` test, `accepted_range`→`dbt_utils.accepted_range` (or `accepted_values`), `custom_checks[]`→singular test `.sql` files under `tests/`, `unit_tests[]`→a `unit_tests:` block in the model's schema yml. In `to_sqlmesh.py`, change the unknown-check branch: the SQLMesh-native set still maps to audits; the dbt-only set (`relationships`, `not_empty`, `custom_checks`, `unit_tests`) is `log.debug`-skipped rather than `SqlSpecError`. In `to_bruin.py`, these pass through natively (Bruin reads `@bruin` checks directly). Set `DEFAULT_ENGINES = ("dbt", "bruin")` in `__init__.py`.

- [ ] **Step 4: Run to verify it passes** — same command → PASS. Also `uv run pytest src/tests/unit -k "spec_compile or reroot" -q`.

- [ ] **Step 5: Commit** — `feat(spec-compile): dbt/bruin default targets; route dbt-native DQ, sqlmesh skips it` · `Refs: #40`.

---

## Task 2: Fix the dbt/Dagster combo path (#38) — build with the full source set

**Files:**
- Modify: `spec/sql/staging/stg_metacritic_games.sql`, `stg_psn_concepts.sql`, `stg_steamcharts_apps.sql` (source resilience) OR the dbt combo-e2e harness ingest step.
- Test: `src/tests/e2e/test_all_setups.py::test_combo_dbt_builds` (make the dbt/dagster combo assert green)

**Interfaces:**
- Consumes: the raw landing convention (`<system>__<table>`), the demo-safe fixture scrapers (metacritic/opencritic/psn enabled by default).
- Produces: the dbt build over the dlt→dbt path succeeds even when scraped-source raw is empty — scraped-source staging models resolve against **always-present (possibly empty) raw tables**, and the downstream core models (`critic_reception`/`console_pricing`/`traction`) emit zero rows rather than erroring.

- [ ] **Step 1: Write the failing test** — the combo dbt path builds to FS without `Table does not exist`.

```python
def test_combo_dbt_builds_with_scraped_sources_absent(tmp_path, monkeypatch):
    # dlt path lands only rawg; scraped-source raw is empty but MUST exist as a relation
    result = run_setup("dbt")  # build staging→core→fs via dbt
    assert result["fs.market_features"] >= 1        # rawg spine survives
    assert result["core.critic_reception"] == 0     # no metacritic match → zero rows, not error
```

- [ ] **Step 2: Run to verify it fails** — reproduces the #38 `Catalog Error: Table with name stg_metacritic_games does not exist`.

- [ ] **Step 3: Implement** — ensure the scraped-source raw tables are **materialized empty** at ingest (the demo-safe scrapers already run fixture-driven; make the dbt `source()` definitions point at raw relations the ingest step guarantees to create even with zero rows). The staging models then build (empty), and the core feature models LEFT JOIN through the bridge → zero matched rows, no missing-table error. Keep the rawg spine intact so `fs.market_features` still has rows.

- [ ] **Step 4: Run to verify it passes** — `uv run pytest src/tests/e2e/test_all_setups.py -k "combo_dbt or dbt" -q` and, with `OGIP_E2E_ALL_ENGINES=1`, the dagster combo job. Confirm the CI `combo-e2e`/`dagster-e2e` job goes green.

- [ ] **Step 5: Commit** — `fix(dbt): combo path builds with empty scraped-source staging (no missing-table)` · `Closes: #38`.

---

## Task 3: Physically move the five demoted sub-projects to experimental/

**Files:**
- Move: `pipelines/{sqlmesh,plain_sql,opendbt,sqlmesh_dbt,dagster}/` → `experimental/pipelines/{...}/`
- Modify: `pipelines/_shared/engines.py`, `src/tests/unit/test_prefect_subprojects.py`
- Create: `experimental/pipelines/README.md`

**Interfaces:**
- Consumes: `ENGINE_FLOWS` (transform-name → module path), `make_engine_flow`.
- Produces: `ENGINE_FLOWS = {"dbt": "pipelines.dbt.flow", "bruin": "pipelines.bruin.flow", "sqlmesh": "experimental.pipelines.sqlmesh.flow", "plain_sql": "experimental.pipelines.plain_sql.flow", "opendbt": "experimental.pipelines.opendbt.flow", "sqlmesh_dbt": "experimental.pipelines.sqlmesh_dbt.flow", "dagster": "experimental.pipelines.dagster.flow"}`.

- [ ] **Step 1: Write the failing test** — the subproject test asserts the new locations.

```python
_PRIMARY = ["dbt", "bruin"]                                   # in pipelines/
_EXPERIMENTAL = ["sqlmesh", "plain_sql", "opendbt", "sqlmesh_dbt", "dagster"]  # in experimental/pipelines/
def test_primary_subprojects_are_on_the_default_path():
    for e in _PRIMARY:
        assert (Path("pipelines") / e / "flow.py").is_file()
def test_experimental_subprojects_are_moved_off_the_path():
    for e in _EXPERIMENTAL:
        assert (Path("experimental/pipelines") / e / "flow.py").is_file()
        assert not (Path("pipelines") / e).exists()
```

- [ ] **Step 2: Run to verify it fails** — dirs not yet moved.

- [ ] **Step 3: Implement** — `git mv` each of the five dirs into `experimental/pipelines/`; update their `flow.py` imports if any use a moved-relative path (they import from `pipelines._shared`, which is unchanged — verify). Repoint `ENGINE_FLOWS`. Write `experimental/pipelines/README.md` (comparison setups; consume `spec/`; never on the default `make`/pipeline path). Keep `pipelines/flows/main.py` re-export pointing at the PRIMARY: `from pipelines.dbt.flow import flow as ingest_transform_publish`.

- [ ] **Step 4: Run to verify it passes** — `uv run pytest src/tests/unit/test_prefect_subprojects.py -q` + `make check`.

- [ ] **Step 5: Commit** — `refactor(pipelines): move sqlmesh/plain_sql/opendbt/sqlmesh_dbt/dagster to experimental/` · `Refs: #40`.

---

## Task 4: Flip config + run profiles + Makefile default to dbt (bruin co-primary)

**Files:**
- Modify: `config/config.yml` (`run_profiles`), `Makefile`, `pipelines/_shared/steps.py::build_warehouse`
- Test: `src/tests/unit/test_run_profiles.py` (create/extend)

**Interfaces:**
- Consumes: `run_profiles` SSoT, `build_warehouse(engine)`.
- Produces: `prefect-dbt: {default: true}`; `prefect-bruin` co-primary (no `experimental` flag); the five others carry `experimental: true`. `build_warehouse` default branch runs dbt; sqlmesh branch reachable only for the experimental setup.

- [ ] **Step 1: Write the failing test**

```python
def test_default_profile_is_prefect_dbt():
    profiles = get_settings_yaml()["run_profiles"]
    assert profiles["prefect-dbt"].get("default") is True
    assert profiles["prefect-sqlmesh"].get("experimental") is True
    assert "experimental" not in profiles["prefect-bruin"]   # co-primary
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** — edit `config/config.yml`: remove `default: true` from `prefect-sqlmesh`, add to `prefect-dbt`; mark `prefect-sql`/`prefect-opendbt`/`prefect-sqlmesh-over-dbt`/`prefect-over-dagster`/`prefect-dagster-dlt-dbt`/`prefect-sqlmesh` with `experimental: true`. Makefile: `run` → `just run-profile prefect-dbt`; add `run-bruin`; regroup the five under `experimental-run-*` comments. In `build_warehouse`, make dbt the default and gate the sqlmesh branch behind `engine == "sqlmesh"` (already so) — but ensure the DEFAULT engine constant used by `main.py`/`make run` is dbt.

- [ ] **Step 4: Run to verify it passes** — `uv run pytest src/tests/unit/test_run_profiles.py -q` + `make check`.

- [ ] **Step 5: Commit** — `feat(config): prefect-dbt is default; bruin co-primary; rest experimental` · `Refs: #40`.

---

## Task 5: Rewrite AGENTS.md hard rules + production-path narrative

**Files:**
- Modify: `.ai/AGENTS.md`
- Create: `docs/adr/ADR-0020-dbt-bruin-primary-candidates.md`

**Interfaces:** none (docs) — but this is the SSoT the other tasks are judged against, so the wording must match the code.

- [ ] **Step 1** — Rewrite the "production path" section: the production path now runs **dbt** (and Bruin as the co-primary comparison candidate), both generated from `spec/`. Remove "the **only** production transform engine is **SQLMesh**"; replace with "the two primary candidates are dbt and Bruin; SQLMesh, plain-SQL, opendbt, sqlmesh-over-dbt and the Dagster setups are comparison/experimental engines under `experimental/`."
- [ ] **Step 2** — Update Hard rule 2 ("default runtime engine is SQLMesh" → "default runtime engine is dbt; Bruin is the co-primary; spec authoring stays `@bruin`"). Update the "Run & orchestration profiles" list (default = `prefect-dbt`).
- [ ] **Step 3** — Write ADR-0020 (verify it's the next free number — last was 0019; grep to avoid the OGAP collision). Record: decision, the demotion, the #38/#34 dependencies, why physical move over labels-only (user choice), and that this reverses ADR-era "SQLMesh is production" wording.
- [ ] **Step 4** — `grep -rn "only production transform engine is\|default runtime engine is SQLMesh" .` returns nothing stale.
- [ ] **Step 5: Commit** — `docs(agents): dbt+bruin are the primary candidates; sqlmesh → experimental (ADR-0020)` · `Refs: #40`.

---

## Task 6: Tests — drift guard + primary e2e + DQ execution in the gate

**Files:**
- Modify: `src/tests/unit/test_engine_projects_cover_spec.py`, `src/tests/e2e/test_all_setups.py`, `Makefile` (`check` target)

**Interfaces:**
- Produces: `make check` runs the two primaries' real DQ (dbt `build` runs dbt tests incl. #34's; Bruin `validate` reads native `@bruin` checks) — closing the audit-execution gap FOR THE PRIMARIES (the sqlmesh-audit-deselect gap, ogip-dq-projection-and-gate-gap, stays only for the now-experimental sqlmesh).

- [ ] **Step 1** — Extend the drift guard: the committed snapshots `transform/dbt/` and `transform/bruin/` must cover all spec models (they already do); regenerate via `uv run python -m ogip.spec_compile all`. sqlmesh snapshot stays gitignored + guarded by a direct compile call.
- [ ] **Step 2** — In `test_all_setups.py`, make the **dbt and bruin** base-setup e2e run in the DEFAULT selection (not behind `OGIP_E2E_ALL_ENGINES=1`); move sqlmesh/opendbt/sqlmesh_dbt/dagster behind the flag.
- [ ] **Step 3** — `make check`: ensure the dbt+bruin e2e (which executes their DQ) is NOT deselected — this is the gate-parity the labels-only option would have skipped. Keep the heavy experimental engines deselected.
- [ ] **Step 4** — `make check` green; `OGIP_E2E_ALL_ENGINES=1 uv run pytest src/tests/e2e -q` green.
- [ ] **Step 5: Commit** — `test(reroot): dbt+bruin e2e+DQ run in the gate; experimental engines behind the flag` · `Refs: #40`.

---

## Task 7: Regenerate snapshots + docs sweep

- [ ] **Step 1** — `uv run python -m ogip.spec_compile all`; commit regenerated `transform/dbt/`, `transform/bruin/`.
- [ ] **Step 2** — Update `pipelines/README.md`, `transform/README.md`, `README.md`, `config/README.md` for the new default; every moved dir keeps/gets a `README.md`.
- [ ] **Step 3** — `grep -rn "prefect-sqlmesh (default\|production).*SQLMesh"` docs → none stale.
- [ ] **Step 4: Commit** — `docs(reroot): sweep READMEs + regenerate dbt/bruin snapshots` · `Refs: #40`.

---

## Task 8: Compact the ODOS monitoring/DQ story for the primaries (optional, if in scope)

Route freshness/row-count monitors (`spec/dq/policy.yml`) to run against the dbt/bruin primary warehouse in `dq/run.py` (still Phase-4 execution — keep as load+report unless the user pulls execution into this slice). Skip if the user wants the re-root kept mechanical.

---

## Task 9: Materialize the pre-flight scripts (in-repo, per code standards)

**Files:**
- Create: `src/scripts/preflight-clean-ground.sh`, `src/scripts/gh-merge-as.sh`
- Modify: `Justfile` (passthrough recipes), `config/config.yml` (any scalars: host `github.com`, primary branch `dev`)

- [ ] **Step 1** — `preflight-clean-ground.sh`: the recon this plan's preconditions need — worktree table (dirty/ahead-behind/merged), open PRs + mergeable + CI rollup, stale-lock + patch-id-duplicate detection, verdict `clean|not-clean + blockers`. Read-only. Scalars (branch, host) from `config/config.yml`.
- [ ] **Step 2** — `gh-merge-as.sh <pr>`: `gh auth switch -u dataengy` → `gh pr merge` → restore prior account; refuses if the action is classifier-gated (prints the manual instruction). Encodes [[ogip-gh-merge-account-and-classifier]].
- [ ] **Step 3** — Wire both into `Justfile` (`preflight`, `merge-as` recipes); `shellcheck -S error` clean; add to `bash-lint`.
- [ ] **Step 4: Commit** — `feat(scripts): preflight-clean-ground + gh-merge-as (in-repo, code-standard)` · `Refs: #40`.

> **Catalog-skill note:** `/land-conflicting-pr` and the ruff-parity / combo-e2e hooks (#39/#38) are proposed as SHARED-CATALOG skills/hooks, built via `/create-skill` + `/save-all-deterministic-for-skill-as-scripts` (never hand-written). They are out of this in-repo plan's scope; raise them separately once the catalog tooling is available in-session.

---

## Self-Review

- **Spec coverage:** demotion (T3/T4), narrative (T5), compiler primacy + #34 DQ (T1), #38 fix (T2), gate parity (T6), snapshots/docs (T7), scripts (T9), #39 handled in T5's ADR + T9 note. ✔
- **Ordering:** T1→T2 (compiler + dbt-path green) BEFORE T3/T4 (the move), so the primaries are proven green before they become the only default. T5/T6/T7 after. ✔
- **Dependency on #29:** stated in Global Constraints (it moves `pipelines/_shared/steps.py` + `main.py`). ✔
- **Type consistency:** `ENGINE_FLOWS` keys identical across T3; `DEFAULT_ENGINES=("dbt","bruin")` used in T1/T4/T6. ✔
- **Risk:** largest blast radius; the worktree+PR isolation + T1/T2-before-move sequencing contain it. ADR-0020 records the reversal of the "SQLMesh is production" hard rule.

## Execution Handoff

Plan saved. Two execution options: **(1) Subagent-Driven (recommended)** — fresh subagent per task + two-stage review; **(2) Inline** — executing-plans with checkpoints. Execution starts once **PR #29 is merged** and the worktree is branched off post-#29 `dev`.
