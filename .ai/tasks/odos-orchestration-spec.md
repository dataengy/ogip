# Task — `spec/orchestration`: `@odos 0.1` orchestration standard (Dagster + Prefect)

**Status:** 📋 planned · **Priority:** mid · **Suggested model:** Opus 4.8 @ `high`

Lane: `orchestration`. Scope: `spec/orchestration/`, `src/ogip/tasks/`,
`src/ogip/spec_compile/`, `experimental/orchestration/dagster_ogip/`, `pipelines/flows/`.
Issue: [#37](https://github.com/dataengy/ogip/issues/37).
Design: [2026-07-20 ODOS design](../../docs/superpowers/specs/2026-07-20-odos-orchestration-spec-design.md).
Sibling format: [ADR-0016](../../docs/adr/ADR-0016-odts-authoring-format-spec-sql.md) (`@odts`).
Related: [#13](https://github.com/dataengy/ogip/issues/13) (Dagster setup),
[#31](https://github.com/dataengy/ogip/issues/31) (per-engine Prefect setups).

## Goal

**ODOS** (Open Data **Orchestration** Standard) — the orchestration sibling of ODTS under the
**ODPS** umbrella. One engine-agnostic description of *when, in what order, and how it survives
failure*, compiled into both orchestrators OGIP runs: Dagster 1.13.x and Prefect ≥3.4.

ODTS says what is computed; ODOS says when it runs. Neither describes the other.

## Why

Orchestration is defined **twice** today, in two dialects — `jobs/dg-tasks.sh` (bash, wired to
Dagster) and `pipelines/flows/_common.py` (Python, wrapped by Prefect) — and **they have already
drifted**. The same logical step, "ensure raw exists", is conditional and routed through the
orchestrator on the Dagster side (`ensure_raw`, `dg launch`), unconditional and straight to dlt on
the Prefect side (`ingest_raw`). Nothing detects this. It is the orchestration-layer analogue of
ODTS's `sk = md5(id)` hazard: valid, runnable, silently different.

## Sketch

- [ ] **R&D first — verify the Prefect surface by running it** (§13.1 of the design). Can OSS
      Prefect ≥3.4 express `on: asset_materialized` and `on: poll` natively, or must both project
      to scheduled deployments with an external cursor? A third of the capability matrix depends
      on the answer. Do not assume — ADR-0016's warning applies.
- [ ] **Task registry** `src/ogip/tasks/` — `@odos_task("dbt.build")` over plain typed functions.
      Collapses `dg-tasks.sh` + `_common.py`; six of nine bash tasks become
      `dbt.build(full_refresh=, select=, state=)`. Decide the `ensure_raw` semantics (conditional
      or not) — it is a behaviour change for whichever lane loses.
- [ ] **IR + frontend** — Pydantic v2, `_defaults` merge, `select:` expansion against the
      ODTS-derived asset graph, registry-name validation, closed key set (unknown key = error).
- [ ] **Adapters** `to_dagster.py` / `to_prefect.py`; capability matrix enforced — an
      unprojectable object without `targets:` fails the compile, never drops silently.
- [ ] **Write the six group files** covering the whole `dagster_ogip` code location.
- [ ] **ADR-0017** recording the decision (verify the number is free — ADR numbering has collided
      with OGAP before).
- [ ] Gates: `just spec-compile all`, `just spec-verify`, `make check` green.

## Equivalence test — non-negotiable

The counterpart of ODTS's macro conformance test, and for the same reason: two renderings of one
spec are two chances to diverge, silently.

For every job present in both projections, assert the **same ordered sequence of registry task
names with the same args**. This is exactly what would have caught the `ensure_raw` drift above.
A job that compiles to both targets without a passing equivalence test does not land.

## Non-goals

- Describing transformations (ODTS owns that).
- Instance/deploy config — `dagster.yaml`, storage, run coordinator. That is `config/config.yml`
  per hard rule 3; duplicating it creates a second SSoT.
- A third orchestrator before one is actually adopted.
- Open key pass-through (dag-factory's model) — incompatible with two unequal targets.

## Open questions

Carried from §13 of the design doc: Prefect event surface (above) · `ensure_raw` semantics · flat
`automations:` vs triggers nested under jobs · whether the `monitoring` group survives once
`on_failure:` is defaulted.

## Acceptance

- `spec/orchestration/*.yml` describes the whole `dagster_ogip` location; `dg check defs` green
  against the compiled Dagster output.
- Both adapters compile; `just spec-verify` green.
- Equivalence test present and green; deliberately desyncing one adapter turns it red.
- ODTS/ODOS naming reconciled with the ODPS taxonomy (handoff to the `spec` lane — ODTS is
  currently expanded as "Spec", and `spec/sql/AGENTS.md:16` says "not a published standard").
