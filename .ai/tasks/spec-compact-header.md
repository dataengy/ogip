# Task — `spec/sql`: `@odts 0.1` compact header (frontend → `@bruin` YAML)

**Status:** 📋 planned · **Priority:** mid · **Suggested model:** Opus 4.8 @ `high`

Lane: `spec`. Scope: `spec/`, `src/ogip/spec_compile/`. Issue: [#35](https://github.com/dataengy/ogip/issues/35).
Decided in [ADR-0016](../../docs/adr/ADR-0016-odts-authoring-format-spec-sql.md); working
rules in [spec/sql/AGENTS.md](../../spec/sql/AGENTS.md).

## Goal

Replace the verbose `@bruin` YAML header with the compact line-oriented `@odts 0.1` header,
**without touching the adapters**: a frontend renders `@odts` → `@bruin` YAML text, and the
existing `parse_asset()` pipeline continues unchanged.

```
spec/sql/**/*.sql (@odts, SSoT) ──▶ rendered @bruin YAML ──▶ parse_asset() ──▶ adapters
```

Run **after** [spec-macros.md](spec-macros.md) — that task settles macro syntax inside the
body, this one settles the header around it.

## Why YAML text, not straight to `Asset`

`to_bruin` copies asset files **verbatim**, so the Bruin target needs real `@bruin` header
text regardless. Rendering it is required by an existing target; skipping the intermediate
would buy nothing and hide a step.

## Sketch

- [ ] Parser for the `@odts 0.1` header — recursive descent, one directive per line
      (`model` · `kind` · `owner` · `tags` · `depends` · `columns` · `checks` · `imports`),
      plus the indented column-attribute block.
- [ ] Renderer → `@bruin` YAML; **round-trip test** against every current model so the
      generated YAML is provably equivalent to today's hand-written header.
- [ ] Marker dispatch in `parse_asset()`: `/* @odts` → frontend, `/* @bruin` → legacy path.
      Both valid during migration.
- [ ] **Inference, not authoring**: drop `type: duckdb.sql` (derivable). Make `depends`
      optional — derive via `dialect.table_refs()`, and when written, treat it as an
      assertion: **fail the compile if it disagrees with the AST**.
- [ ] LValue desugaring: rewrite `PropertyEQ` → aliased projection, **only** as a direct
      child of the projection list. Nested `:=` is a DuckDB named argument — leave it alone.
      Reject `EQ` in a projection with a clear error pointing at `:=`.
- [ ] Convert the four existing models; rendered YAML is **never committed**.
- [ ] Update [spec/README.md](../../spec/README.md) (format column still says "Bruin asset")
      and the `spec/` format note in [ADR-0005](../../docs/adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md)'s
      wake — ADR-0005 stays immutable; ADR-0016 supersedes the format detail.

## Target shape

16 header lines → 8, with `type` and `depends` inferred:

```
/* @odts 0.1
model     core.game
kind      table
owner     data-eng@ogip
tags      core, entity, daily

columns:
  game_sk   varchar   pk !null unique
  title     varchar   !null
*/
```

## Verify by running, not assuming

Parser assumptions about sqlglot/sqlfluff/DuckDB have already been wrong twice in this design
— both times as "it parses, therefore it works". Check behaviour against the pinned versions
(sqlglot 30.8.0 · DuckDB 1.5.4 · sqlfluff 4.2.2) rather than reasoning about it.

## Acceptance

- All models in `spec/sql` authored as `@odts 0.1`; no committed YAML duplicates.
- Round-trip test proves rendered YAML ≡ the previous hand-written headers.
- A `depends` that contradicts the SQL AST fails the compile.
- `select x = y` in a projection is rejected with an actionable error; `select x := y` works.
- `just spec-compile all` · `just spec-verify` · `just sql-lint` · `make check` green.
