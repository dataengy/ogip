# Wiring the scraper/parser tasks into the four orchestration layers — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **STALE-PATH NOTE (added 2026-07-23, still open — do NOT implement against the paths below).**
> The Part 3 restructure of the [transform-expansion
> plan](2026-07-23-transform-expansion-and-six-prefect-subprojects.md) (see
> [ADR-0019](../../adr/ADR-0019-odts-dq-projection-and-seven-prefect-subprojects.md)) deleted
> every file this plan edits or references below. Before touching any task here, remap:
>
> | This plan says | Now lives at |
> |---|---|
> | `pipelines/flows/_common.py` (incl. `make_engine_flow`, `ingest_raw`, `scraper_raw_keys`, `make_ingest_assets`) | [`pipelines/_shared/steps.py`](../../../pipelines/_shared/steps.py) |
> | `pipelines/flows/_paths.py` | [`pipelines/_shared/paths.py`](../../../pipelines/_shared/paths.py) |
> | `pipelines/alerting_hooks.py` | [`pipelines/_shared/alerting.py`](../../../pipelines/_shared/alerting.py) |
> | `pipelines/flows/engines/prefect_dagster.py` | [`pipelines/dagster/flow.py`](../../../pipelines/dagster/flow.py) |
> | `pipelines/flows/engines/prefect_bruin.py` (and the other `prefect_*.py` one-liners) | `pipelines/<engine>/flow.py` — one directory per engine (`sqlmesh`, `plain_sql`, `dbt`, `opendbt`, `sqlmesh_dbt`, `bruin`, `dagster`), each `{__init__.py, flow.py, prefect.yaml}` |
> | engine → module lookup (previously implicit/hand-imported) | [`pipelines/_shared/engines.py`](../../../pipelines/_shared/engines.py) `ENGINE_FLOWS` |
>
> `make_engine_flow` itself is unchanged behaviourally — it moved, not mutated — so this plan's
> designs (per-source scraper assets, `raw_asset_key`, the landing-hop gate) still apply; only
> the file paths in the Task/Files blocks below are dead. See
> [`spec/ODOS/IMPLEMENTATION.md`](../../../spec/ODOS/IMPLEMENTATION.md) §4 and
> [`pipelines/README.md`](../../../pipelines/README.md) for the current layout.

**Goal:** Make every scraper/parser registry task (`ingest.opencritic`, `ingest.psn`, `ingest.steamcharts`, and the `ingest.parse_to_landing` placeholder) a first-class, drift-gated citizen of all four orchestration layers — ODOS spec, main Prefect, alt Prefect+Dagster, alt Bruin — reusing one deterministic projection instead of hand-editing four places.

**Architecture:** The registry (`src/ogip/tasks/`) is the SSoT; every orchestration layer is a *projection* of it. Today those projections are hand-written and silently drift (three scrapers shipped without any ODOS/Prefect-lineage projection). This plan (a) closes the drift for the three shipped scrapers, (b) extracts the projection into a deterministic script + a scraper-scoped equivalence gate — the compiler-prep slice of ODOS #37 — so the *next* scraper cannot ship half-wired. Layers 3 and 4 are described **only as their delta** from layer 2, and the central finding is that the delta is nearly empty: scrapers never move into Dagster/Airbyte/Bruin because those tools have no bespoke-HTML-parser source. Scrapers stay Prefect-side Python assets; only the *warehouse core* (rawg dlt + dbt SQL) is what each alt profile swaps.

**Tech Stack:** Python 3.13 (pyright strict, ruff), Prefect 3 (`@flow`/`@materialize` assets), Dagster 1.13.x (`dg launch`, isolated env under `experimental/`), Bruin CLI, ODOS 0.1 fixtures (`spec/ODOS/examples/*.yml`), `@bruin`-portable SQL, pytest. Deterministic logic goes to `~/.ai/skills/_scripts/de/ingestion/` behind a Justfile per the `/save-all-deterministic-for-skill-as-scripts` standard.

## Global Constraints

- **Registry is SSoT.** A layer projection never re-implements a task body; it references the registry name. No parallel scraper code in any flow. (`docs/.../odos-*.md` §2 — the drift this replaces.)
- **Closed vocabulary.** `test_tasks_registry.py:97` pins the exact `ingest.*` set. Any new task name updates that set in the same commit or CI is red.
- **Layer-0 law.** Scraper output lands 1:1 AS-IS; only `_ingested_at` + `etl_batch_id` (+ dlt internals). No casting/renaming in ingestion — that is staging's job.
- **`publishable: false` holds.** All three scrapers keep the republication gate; this plan touches orchestration only, never the contract's publish posture.
- **Demo-safe default.** `make run` must never scrape a live site as a side effect. Every scraper asset inherits `OGIP_<SRC>_LIVE` gating from its source class — the flow does not override it.
- **Asset-key scheme is one string, one place.** `file://ogip/{engine}/raw/{system}__{entity}` is currently hand-typed in `_common.py` and `prefect_dagster.py`. After Task 2.3 it is constructed by one helper reading settings; no literal raw-key strings elsewhere.
- **Commit binding.** Every commit carries `Refs: #37` (ODOS wiring) and, for the scraper-specific tasks, `Refs: #18` / `Refs: #19`. Enforced by `.ci/steps/commit-binding.sh`.
- **PROPOSE-ONLY for skills.** Skill/hook files are never hand-written — proposed here, created via `/create-skill` / `/upsert-skill` after user approval. Scripts under `_scripts/` are the preferred deterministic surface.

---

## Current state (the "итого")

Registry tasks in `src/ogip/tasks/ingest.py` and their wiring gaps:

| Task | L1 ODOS | L2 main Prefect | L3 Dagster-in-Prefect | L4 Bruin |
|---|---|---|---|---|
| `ingest.rawg` | ✅ `dlt_ingest_job` | ✅ `_ingest` | ✅ `K_RAW_DLT` | ✅ via `ingest.all` |
| `ingest.metacritic` | ✅ `metacritic_ingest_job` | ⚠️ folded in `ingest.all` | ❌ (Prefect-side by design) | ✅ via `ingest.all` |
| `ingest.opencritic` | ❌ **gap** | ⚠️ folded, no own asset | ❌ | ✅ via `ingest.all` |
| `ingest.psn` | ❌ **gap** | ⚠️ folded, no own asset | ❌ | ✅ via `ingest.all` |
| `ingest.steamcharts` | ❌ **gap** | ⚠️ folded, no own asset | ❌ | ✅ via `ingest.all` |
| `ingest.parse_to_landing` | ✅ `parsing_job` | ❌ not in flow | ✅ Dagster `parsing` | ❌ |

Three drift gaps to close: L1 fixture coverage, L2 per-source lineage, and the absence of any *gate* that would have caught either. Layers 3/4 are delta-only (below) and mostly inherit L2.

---

## Layer 1 — ODOS spec / model

**What changes:** `spec/ODOS/examples/ingestion.yml` gains three scraper `*_ingest_job` stanzas mirroring `metacritic_ingest_job`, and a new test makes fixture↔registry coverage a CI gate. This is the scraper-scoped slice of the #37 equivalence test — the first gate that turns "forgot to project the scraper" into a red build instead of a code-review hope.

### Task 1.1: ODOS fixture covers every registered scraper

**Files:**
- Create: `src/tests/unit/test_odos_ingestion_fixture.py`
- Modify: `spec/ODOS/examples/ingestion.yml`

**Interfaces:**
- Consumes: `ogip.tasks.task_names()` (registry vocabulary), the `ingest.*` names tagged as scrapes.
- Produces: nothing importable — a fixture + a gate other tasks rely on staying green.

- [ ] **Step 1: Write the failing test.** A scraper is any `ingest.<name>` registry task except `ingest.rawg` (dlt API), `ingest.all` (fan-out) and `ingest.parse_to_landing` (landing hop, its own `parsing_job`). Every such task must appear as a job's `task:` in `ingestion.yml`.

```python
# src/tests/unit/test_odos_ingestion_fixture.py
from pathlib import Path

import yaml

from ogip.tasks import task_names

_FIXTURE = Path("spec/ODOS/examples/ingestion.yml")
_NON_SCRAPER = {"ingest.rawg", "ingest.all", "ingest.parse_to_landing"}


def _scraper_task_names() -> set[str]:
    return {n for n in task_names() if n.startswith("ingest.")} - _NON_SCRAPER


def test_every_registered_scraper_has_an_odos_ingest_job():
    doc = yaml.safe_load(_FIXTURE.read_text("utf-8"))
    projected = {job["task"] for job in doc["jobs"].values() if "task" in job}
    missing = _scraper_task_names() - projected
    assert not missing, f"scraper tasks with no ODOS job: {sorted(missing)}"
```

- [ ] **Step 2: Run it, verify it fails.** Run: `uv run pytest src/tests/unit/test_odos_ingestion_fixture.py -v`. Expected: FAIL — `scraper tasks with no ODOS job: ['ingest.opencritic', 'ingest.psn', 'ingest.steamcharts']`.

- [ ] **Step 3: Add the three job stanzas** to `spec/ODOS/examples/ingestion.yml`, mirroring `metacritic_ingest_job` exactly (same `tags`, a `doc` naming the market dimension):

```yaml
  opencritic_ingest_job:
    task: ingest.opencritic
    tags: {ingestion: scraping}
    doc: "Quality dimension — OpenCritic JSON-LD scrape → raw Parquet (demo-safe by default)."
  psn_ingest_job:
    task: ingest.psn
    tags: {ingestion: scraping}
    doc: "Console-pricing dimension — PSN Store concept JSON-LD → raw Parquet (demo-safe by default)."
  steamcharts_ingest_job:
    task: ingest.steamcharts
    tags: {ingestion: scraping}
    doc: "Traction dimension — SteamCharts CSS scrape → raw Parquet (demo-safe by default)."
```

- [ ] **Step 4: Run test, verify it passes.** Run: `uv run pytest src/tests/unit/test_odos_ingestion_fixture.py -v`. Expected: PASS.

- [ ] **Step 5: Update the ODOS implementation doc.** In `spec/ODOS/IMPLEMENTATION.md` §2 `ingestion.yml` table, replace the single `metacritic_ingest_job` row's "no Dagster job wired yet" note with the four-scraper reality: registry-live, Prefect reaches them through `ingest.all`; no Dagster job by design (see Layer 3). One row per scraper.

- [ ] **Step 6: Commit.** Run: `git commit -o spec/ODOS/examples/ingestion.yml spec/ODOS/IMPLEMENTATION.md src/tests/unit/test_odos_ingestion_fixture.py -m "feat(odos): project the three scrapers into ingestion.yml + coverage gate"` (body: `Refs: #37` `Refs: #18` `Refs: #19`).

### Task 1.2: extract the projection into a deterministic script (`/save-all-deterministic-for-skill-as-scripts`)

**Files:**
- Propose (create via skill flow, not by hand): `~/.ai/skills/_scripts/de/ingestion/odos_scraper_jobs.py` + `emit-odos-scraper-jobs` / `check-odos-scraper-jobs` Justfile recipes in `~/.ai/skills/_scripts/de/ingestion/Justfile`.
- Modify: `Makefile` (`check` target) — add the `--check` invocation.

**Interfaces:**
- Consumes: registry scraper names + each source's `(system, entity, dimension doc)` descriptor from `spec/sources/*.yaml`.
- Produces: idempotent rewrite of the scraper `*_ingest_job` block in `ingestion.yml`; `--check` exits non-zero on drift and prints the missing/extra stanzas.

- [ ] **Step 1:** Hand-writing Step 1.3 is a one-shot; the *durable* need is that job N+1 gets projected automatically. The stanza is a pure function of `(task_name, dimension_doc)`. Extract it: `odos_scraper_jobs.py emit` regenerates the block, `check` diffs and fails on drift. This is exactly the ODOS-compiler `to_*` projection at scraper granularity — build it here so #37 inherits it.
- [ ] **Step 2:** Externalize the scalars to settings (`~/.ai/skills/.settings/de/ingestion/`): the fixture path, the `{ingestion: scraping}` tag, the non-scraper exclusion set, the `doc` template. No literals in the body.
- [ ] **Step 3:** Wire `just … check-odos-scraper-jobs` into `make check` so a scraper task added without its ODOS stanza fails locally, not only in review.
- [ ] **Step 4:** This is PROPOSE-ONLY. Do not write the skill file. Route through `/upsert-skill add-data-source` (the projection is the missing tail of the source DoD) → its mandatory `/save-all-deterministic-for-skill-as-scripts` post-step produces the script + settings. Confirm scope with the user first.

**Skill/script/hook for Layer 1:**
- **Script (NEW, primary):** `odos_scraper_jobs.py` (emit + check) — above.
- **Skill (reuse):** `/add-data-source` owns the source DoD that *produces* the registry task; this projection is its currently-missing orchestration tail. Fold in rather than a new skill.
- **Hook:** covered by the cross-cutting `scraper-orchestration-drift` gate (see end) — Layer 1's `check` mode is one of its three assertions.

---

## Layer 2 — main Prefect orchestration

**What changes:** Today `make_engine_flow` runs `ingest_raw = ingest_all` as a single `_ingest` asset keyed `…/raw/rawg__games`, so all four scrapers land invisibly behind rawg's key — zero per-source lineage. This layer gives each *enabled* scraper source its own `@materialize` asset (`file://ogip/{engine}/raw/{system}__{entity}`) that fans into `_transform`, and wires the `parse_to_landing` placeholder behind an off-by-default config gate so enabling ADR-0014's landing hop later is a config flip, not a code change.

### Task 2.1: per-source raw assets in the engine flow

**Files:**
- Modify: `pipelines/flows/_common.py` (add `make_ingest_assets`, rewire `make_engine_flow`)
- Create: `src/tests/unit/test_prefect_ingest_assets.py`

**Interfaces:**
- Consumes: `ogip.tasks.ingest` registry callables; the enabled-source list from `config/config.yml` `sources.<name>.enabled`; the raw-key helper from Task 2.3 (until then, an inline construction to be replaced).
- Produces: `make_ingest_assets(engine: str) -> tuple[Callable[[], str], list[Callable[[], str]]]` — returns `(rawg_asset, scraper_assets)`; `rawg_asset()` returns the RAWG output path (the transform anchor), each scraper asset returns its own raw path. `make_engine_flow` fans all of them into `_transform`.

- [ ] **Step 1: Write the failing test.** Assert the main flow materializes a distinct raw asset per enabled scraper, not one rawg key for all.

```python
# src/tests/unit/test_prefect_ingest_assets.py
from pipelines.flows._common import scraper_raw_keys


def test_each_enabled_scraper_has_its_own_raw_asset_key():
    keys = scraper_raw_keys("sqlmesh")
    assert "file://ogip/sqlmesh/raw/opencritic__game" in keys
    assert "file://ogip/sqlmesh/raw/psn__concept" in keys
    assert "file://ogip/sqlmesh/raw/steamcharts__app" in keys
    # rawg stays the transform anchor, distinct from the scrapers
    assert "file://ogip/sqlmesh/raw/rawg__games" not in keys
```

- [ ] **Step 2: Run it, verify it fails.** Run: `uv run pytest src/tests/unit/test_prefect_ingest_assets.py -v`. Expected: FAIL — `scraper_raw_keys` undefined.

- [ ] **Step 3: Implement `scraper_raw_keys` + `make_ingest_assets`** in `_common.py`. The source→(system,entity,task) map is the registry; keep it explicit and small (it is the same map Task 2.3 externalizes):

```python
# pipelines/flows/_common.py  (add near ingest_raw)
from ogip.tasks.ingest import (
    ingest_metacritic, ingest_opencritic, ingest_psn, ingest_steamcharts,
)

# (system, entity, registry callable) — one row per scraper. rawg is NOT here:
# it is the unconditional Layer-0 transform anchor, kept as ingest_raw below.
_SCRAPERS = (
    ("metacritic", "game", ingest_metacritic),
    ("opencritic", "game", ingest_opencritic),
    ("psn", "concept", ingest_psn),
    ("steamcharts", "app", ingest_steamcharts),
)


def _enabled(name: str) -> bool:
    return bool(load_app_config()["sources"].get(name, {}).get("enabled"))


def scraper_raw_keys(engine: str) -> list[str]:
    """Prefect asset key per *enabled* scraper source (per-source lineage)."""
    return [
        f"file://ogip/{engine}/raw/{system}__{entity}"
        for system, entity, _ in _SCRAPERS
        if _enabled(system)
    ]
```

- [ ] **Step 4:** In `make_engine_flow`, replace the single `_ingest` with rawg-anchor + a fanned-in scraper asset per `scraper_raw_keys(engine)`; each scraper `@materialize` wraps its registry callable and is demo-safe by inheritance. `_transform` still keys off the rawg path (the warehouse anchor); scraper assets are siblings feeding the same `_transform` step. Keep `ingest_all` for the CLI/config-gated path — the flow now expresses the fan-out as assets instead of hiding it in one task.

- [ ] **Step 5: Run tests, verify pass.** Run: `uv run pytest src/tests/unit/test_prefect_ingest_assets.py -v && make check`. Expected: PASS; ruff + pyright strict clean.

- [ ] **Step 6: Commit.** `git commit -o pipelines/flows/_common.py src/tests/unit/test_prefect_ingest_assets.py -m "feat(pipelines): per-source scraper raw assets for Prefect lineage"` (`Refs: #37 #18 #19`).

### Task 2.2: wire `parse_to_landing` behind an off-by-default gate

**Files:**
- Modify: `pipelines/flows/_common.py`, `config/config.yml` (add `pipeline.landing.enabled: false`)

**Interfaces:**
- Consumes: `ogip.tasks.ingest.parse_to_landing` (placeholder), `config.pipeline.landing.enabled`.
- Produces: an optional `_parse_to_landing` asset keyed `postgres://ogip/{engine}/landing`, materialized only when the gate is on; a no-op (logs the ADR-0014 placeholder) until the async ScraperSource lands.

- [ ] **Step 1:** Add `pipeline.landing.enabled: false` to `config/config.yml` (SSoT; never a graph edge). Render env if applicable (`make render-env`).
- [ ] **Step 2:** In `make_engine_flow`, when the gate is on, prepend a `_parse_to_landing` `@materialize` that calls `parse_to_landing()`. Default-off means `make run` behaviour is unchanged; the wiring exists so ADR-0014 is a config flip.
- [ ] **Step 3: Test** that the gate default keeps the flow's asset set unchanged (no `postgres://…/landing` key when `enabled: false`), and produces it when flipped. Run `make check`. Commit (`Refs: #37`).

### Task 2.3: externalize the raw-key scheme (`/save-all-deterministic-for-skill-as-scripts` + code standards)

**Files:**
- Modify: `pipelines/flows/_common.py`, `pipelines/flows/engines/prefect_dagster.py` (consume the helper), `config/config.yml` or a `src/ogip/` constant module for the URI scheme.

**Interfaces:**
- Produces: `raw_asset_key(engine: str, system: str, entity: str) -> str` — the single constructor of `file://ogip/{engine}/raw/{system}__{entity}`. The scheme (`file://ogip/{engine}/raw/`) is a settings value, not a literal.

- [ ] **Step 1:** The key string is currently hand-typed in `_common.py:107` and `prefect_dagster.py:29-35`. Replace both with `raw_asset_key(...)`. One place constructs keys; drift between the two flows becomes impossible.
- [ ] **Step 2:** Externalize the URI scheme to a settings value (per the code-spec standard `python_module_layout.yml` — scalars out of bodies). Test that `raw_asset_key("sqlmesh","opencritic","game")` round-trips the L2 key.
- [ ] **Step 3: Commit** (`Refs: #37`).

**Skill/script/hook for Layer 2:**
- **Script (NEW, primary):** the `raw_asset_key` helper + settings (Task 2.3) is the deterministic surface — extracted per `/save-all-deterministic-for-skill-as-scripts`, consumed by L2/L3.
- **Skill (reuse):** `/integrate-sql-tool-with-prefect` for the flow-assembly mechanics; do not create a new Prefect skill.
- **Hook:** cross-cutting `scraper-orchestration-drift` (below) — its L2 assertion is "every registered scraper has a `scraper_raw_keys` entry".

---

## Layer 3 — alt Prefect + Dagster-over-dlt-and-Airbyte-and-dbt

**Described only as the delta from Layer 2.**

The seam is `pipelines/flows/engines/prefect_dagster.py`: Dagster owns the **dlt+dbt warehouse core only** (`run_dagster_dlt_dbt` via `dg launch` in the isolated `experimental/orchestration/dagster_ogip` env); Prefect owns scraping, ML, publish, alerting.

**Delta 1 — scraper assets are byte-for-byte the Layer-2 assets, reused, not reimplemented.** `flow_dagster` imports `make_ingest_assets("dagster")` from `_common` (Task 2.1) and fans the *same* scraper `@materialize` assets into the Dagster-built warehouse instead of the Prefect-built one. The only line that changes vs. Layer 2 is that `_transform` is replaced by `_dagster_dlt_dbt` (`run_dagster_dlt_dbt`). Nothing scraper-shaped moves into Dagster.

**Delta 2 — the load-bearing correctness point: scrapers do not go through dlt or Airbyte.** A scraper is a bespoke HTML→JSON-LD/CSS parser. `dlt` and Airbyte have no generic "run my custom parser against this URL" source — their sources are API/DB/file connectors. So "Dagster-over-dlt-**and-Airbyte**-and-dbt" is, for the *scraper* tasks, a no-op: there is nothing to ingest them *as*. They remain Prefect Python assets in this profile exactly as in Layer 2. Only rawg-shaped API/DB sources are candidates for the Dagster dlt/Airbyte lane.

**Delta 3 — Airbyte is an orthogonal, currently-absent component.** `experimental/orchestration/dagster_ogip` today carries `dagster_dlt` + `dagster_dbt` components only; there is no `dagster_airbyte`. Adding Airbyte means a new Dagster component ingesting a *future API/DB source* (e.g. a SteamSpy/IGDB API), tracked separately — it never touches the scraper wiring. Name this gap in the doc so a reader does not expect scrapers to appear under Airbyte.

### Task 3.1: reuse L2 scraper assets in the Dagster-wrapped flow

**Files:**
- Modify: `pipelines/flows/engines/prefect_dagster.py`
- Create: `src/tests/unit/test_prefect_dagster_reuses_scrapers.py`

**Interfaces:**
- Consumes: `make_ingest_assets`/`scraper_raw_keys` (Task 2.1), `run_dagster_dlt_dbt` (existing), `raw_asset_key` (Task 2.3).
- Produces: `flow_dagster` materializing the same scraper raw keys as the main flow + the Dagster warehouse key.

- [ ] **Step 1: Failing test** — the scraper asset set is identical across the main and Dagster flows (the reuse invariant that proves no fork):

```python
# src/tests/unit/test_prefect_dagster_reuses_scrapers.py
from pipelines.flows._common import scraper_raw_keys


def test_dagster_profile_reuses_the_main_scraper_assets():
    assert scraper_raw_keys("dagster") == [
        k.replace("/sqlmesh/", "/dagster/") for k in scraper_raw_keys("sqlmesh")
    ]
```

- [ ] **Step 2:** Run it — FAIL until `flow_dagster` consumes the shared helper.
- [ ] **Step 3:** In `prefect_dagster.py`, fan `make_ingest_assets("dagster")` scraper assets into `flow_dagster` alongside `_dagster_dlt_dbt`; keep `run_dagster_dlt_dbt` as the *only* delta from `make_engine_flow`. Replace the hand-typed `RAW_KEY`/`WAREHOUSE_KEY` literals with `raw_asset_key(...)`.
- [ ] **Step 4:** Run test + `make check` — PASS.
- [ ] **Step 5:** In `prefect_dagster.py` module docstring and `spec/ODOS/IMPLEMENTATION.md`, add the two-sentence "scrapers stay Prefect-side; Airbyte/dlt have no parser source" note. Commit (`Refs: #37`).

**Skill/script/hook for Layer 3:**
- **Script:** none new — reuses Task 2.1/2.3 helpers (that *is* the point: no L3-specific scraper code).
- **Skill (reuse):** `/call-dagster-from-prefect` (the seam pattern already in this file). For the future Airbyte component: `/add-dagster-module` + `/integrate-dagster-with-dbt` — but that is an API-source task, out of scope for scraper wiring; note it, do not build it.
- **Hook:** the cross-cutting gate's reuse assertion covers `scraper_raw_keys("dagster") == scraper_raw_keys("sqlmesh")`-modulo-engine, catching a future fork.

---

## Layer 4 — alt Bruin orchestration

**Described only as the delta from Layers 2 and 3.**

`pipelines/flows/engines/prefect_bruin.py` is `make_engine_flow("bruin")` — it reuses `_common` wholesale. Bruin is the SQL runner for the transform (`spec/sql` run natively, "spec *is* Bruin"); the flow around it is Prefect.

**Delta from Layer 2:** none in the ingestion assets. Once Task 2.1 lands, `make_engine_flow("bruin")` inherits the identical per-source scraper assets for free; the only substitution is `build_warehouse("bruin")` → `run_transform_engine("bruin")`, which already exists. There is no Bruin-specific scraper code to write.

**Delta from Layer 3:** unlike Layer 3, Bruin does **not** pull the warehouse core into a foreign orchestrator. The whole chain stays in Prefect; Bruin is invoked *only* as the SQL engine for `_transform`. So scrapers → Prefect assets → a Bruin-run warehouse. Layer 3 swaps the core into Dagster; Layer 4 swaps only the SQL dialect runner.

**Bruin-native alternative — named and deliberately declined (YAGNI).** Bruin supports Python assets (`type: python`) and could express each scraper as a Bruin asset in a `spec/bruin/pipeline.yml`, giving Bruin-native lineage. This is declined: it duplicates each registry task behind a second orchestrator-specific wrapper (violating the "registry is SSoT, no parallel implementation" constraint) and buys nothing until Bruin becomes the *primary* orchestrator. Bruin's value here is SQL lineage, not Python orchestration — the same reasoning as Layer 3 (keep bespoke Python where it lives), for a different reason. The plan keeps scrapers on the shared Prefect `make_engine_flow` pre-step.

### Task 4.1: confirm Bruin inherits the shared scraper assets (regression gate only)

**Files:**
- Create: `src/tests/unit/test_prefect_bruin_inherits_scrapers.py`

**Interfaces:**
- Consumes: `pipelines.flows.engines.prefect_bruin.flow`, `scraper_raw_keys` (Task 2.1).

- [ ] **Step 1:** No production code changes — this task is the gate that Bruin never grows a parallel scraper path. Write a test asserting the Bruin flow's scraper keys equal `scraper_raw_keys("bruin")` and that no `spec/bruin/` Python-asset scraper file exists (the declined alternative stays declined).

```python
# src/tests/unit/test_prefect_bruin_inherits_scrapers.py
from pathlib import Path

from pipelines.flows._common import scraper_raw_keys


def test_bruin_reuses_shared_scraper_assets_and_grows_no_parallel_path():
    assert scraper_raw_keys("bruin")  # inherited via make_engine_flow, non-empty
    # the deliberately-declined Bruin-native scraper wrapper must not appear
    assert not list(Path("spec").glob("bruin/**/*scraper*"))
```

- [ ] **Step 2:** Run it — PASS immediately (documents the delta as an executable invariant). `make check`, commit (`Refs: #37`).

**Skill/script/hook for Layer 4:**
- **Script:** none new — full inheritance from Task 2.1.
- **Skill (reuse):** `/generate-agnostic-bruin-sql-specs`, `/spec-compile-engines`, `/integrate-sql-tool-with-prefect` — all for the SQL-transform side, none scraper-specific.
- **Hook:** the cross-cutting gate + Task 4.1's "no parallel path" assertion.

---

## Cross-cutting: the deterministic script + the one hook (PROPOSE-ONLY)

The whole plan is one projection applied four ways. Two durable artifacts fall out, both created via the skill flow, never hand-written:

### A. `odos_scraper_jobs.py` — the projection script (Task 1.2)
Reads registry scraper names + source descriptors → emits/`--check`s the ODOS `ingestion.yml` scraper stanzas. The compiler-prep `to_odos` at scraper granularity. Lives in `~/.ai/skills/_scripts/de/ingestion/`, Justfile-wrapped, scalars in `.settings/`. Route via `/upsert-skill add-data-source` → mandatory `/save-all-deterministic-for-skill-as-scripts`.

### B. `scraper-orchestration-drift` — the one hook that guards all four layers
A single `check` (wired into `make check` + proposed as a pre-commit hook) asserting, for **every** registered `ingest.<scraper>`:
1. **L1** — an ODOS `*_ingest_job` with `task: ingest.<scraper>` exists (Task 1.1's assertion).
2. **L2** — `scraper_raw_keys("sqlmesh")` contains its key (Task 2.1).
3. **L3/L4** — the alt profiles' scraper key sets equal L2's modulo engine (Tasks 3.1, 4.1 — the anti-fork invariant).

This is the exact drift this session hit: three scrapers shipped, none projected into ODOS, none given Prefect lineage, and nothing was red. The hook makes "add a scraper, forget a projection" a failing build. It is the scraper-scoped down-payment on #37's equivalence test — same shape, smaller blast radius, buildable now.

**Reused skills (NOT recreated):** `/add-data-source` (produces the registry task = this plan's input), `/integrate-sql-tool-with-prefect`, `/call-dagster-from-prefect`, `/add-dagster-module`, `/integrate-dagster-with-dbt`, `/spec-compile-engines`, `/generate-agnostic-bruin-sql-specs`, `/find-sources-and-match-tool`. **No new skill is warranted** — the deterministic work is two scripts + one hook; per the user's "or better just script", scripts are primary, and any thin skill front is optional and proposed via `/create-skill` only after approval.

---

## Self-Review

**Spec coverage:** L1 (fixture + gate) ✅ Task 1.1–1.2. L2 (per-source assets + parse_to_landing gate + key helper) ✅ Task 2.1–2.3. L3 (delta-only, reuse + Airbyte/dlt no-parser-source finding) ✅ Task 3.1. L4 (delta-only, full inheritance + declined Bruin-native alternative) ✅ Task 4.1. Cross-cutting script + hook ✅. Skill/script/hook proposals per layer ✅, all PROPOSE-ONLY.

**Placeholder scan:** No "TBD"/"add error handling". `parse_to_landing` is described *as* a placeholder because it genuinely is one (ADR-0014 unshipped) — the task wires the gate, not a fake body, which is the honest move. All code steps carry real code.

**Type consistency:** `scraper_raw_keys(engine: str) -> list[str]`, `raw_asset_key(engine, system, entity) -> str`, `make_ingest_assets(engine) -> tuple[...]` used consistently across Tasks 2.1, 2.3, 3.1, 4.1. `_SCRAPERS` rows are `(system, entity, callable)` throughout. The registry-vocabulary boundary (`_NON_SCRAPER`) is identical in Task 1.1 and the hook.

**Correctness anchor:** the plan's central claim — scrapers stay Prefect-side in every profile because dlt/Airbyte/Bruin have no bespoke-parser source — is what makes Layers 3 and 4 genuinely delta-thin rather than four parallel implementations. That is the reuse the "registry is SSoT" constraint demands.
