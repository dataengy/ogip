# Task — `spec/sql`: `@odts` macro layer (registry + native per-engine adapters)

**Status:** 📋 planned · **Priority:** mid · **Suggested model:** Sonnet 5 @ `high`

Lane: `spec`. Scope: `spec/`, `src/ogip/spec_compile/`. Issue: [#36](https://github.com/dataengy/ogip/issues/36).
Decided in [ADR-0016](../../docs/adr/ADR-0016-odts-authoring-format-spec-sql.md); working
rules in [spec/sql/AGENTS.md](../../spec/sql/AGENTS.md).

## Goal

Give `spec/sql` semantic macros — `@ns.name(args)` — defined once and compiled **natively per
engine**, so the production engine's own macro system is used rather than routed around.

## Why this is first

Smaller than the compact header, and the call sites already exist: `core/game.sql` hand-writes
`md5(cast(game_id as varchar))` and `extract(year from released_date)`.

## Sketch

- [ ] Registry — one macro definition carrying semantics + per-target rendering. Start with
      **exactly two**: `@keys.hash`, `@dates.year`. No library built ahead of demand.
- [ ] Frontend: recognise `@ns.name(...)` in the SQL body; resolve `imports:` (no globals).
- [ ] Adapters:
      - `to_sqlmesh` → emit `@DEF(...)` from the registry, keep call sites as `@`
      - `to_dbt` / `to_sqlmesh_dbt` / `to_bruin` → Jinja
      - plain-SQL runner → expand to native SQL
- [ ] **Conformance test** (the point of the whole task, see below).
- [ ] Convert the two `core/game.sql` call sites; `just spec-verify` stays green.
- [ ] Document the registry in [spec/README.md](../../spec/README.md).

## Prior art agrees with the design — and stops one step short

[OTS](https://github.com/francescomucio/open-transformation-specification) arrived at the same
shape independently: its `functions` carry `code.generic_sql` **plus** `code.database_specific`
keyed by database — one semantic definition, per-engine renderings, exactly the registry below
([full assessment](../../docs/comparisons/ots-vs-odts.md)).

It does **not** specify how the renderings are kept in agreement. That gap is the conformance
test, which is therefore the part of this task with no prior art to lean on — and the part most
likely to be cut under time pressure. Do not cut it.

## Conformance test — non-negotiable

Compiling one macro into four native implementations is four chances to diverge, and the
failure is silent: `dbt_utils.generate_surrogate_key` does **not** hash like
`md5(cast(x as varchar))`, so the same model would key differently depending on the run
profile — a data incident discovered far downstream, if ever.

The test: for each macro, one fixture table, executed through **every** adapter on DuckDB,
asserting byte-identical output. A macro without a passing conformance test does not land.

## Acceptance

- `@keys.hash` / `@dates.year` used in `spec/sql`, resolved through `imports:`.
- `just spec-compile all` green; SQLMesh output contains real `@DEF` + `@` call sites.
- Conformance test present and green for both macros; deliberately breaking one adapter's
  rendering turns it red.
- `make check` + `just sql-lint` + `just spec-verify` green.
