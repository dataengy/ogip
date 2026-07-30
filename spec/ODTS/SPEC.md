# ODTS 0.1 normative profile

**Status:** approved OGIP profile
**Version:** 0.1
**Scope:** the `@odts` authoring format for `spec/sql`, compiled to OGIP's six targets
(SQLMesh · dbt · OpenDBT · SQLMesh-over-dbt · Bruin · plain SQL)

The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative. Sources of
authority: the [governing brief](GOVERNING-BRIEF.md) (design principles),
[ADR-0016](../../docs/adr/ADR-0016-odts-authoring-format-spec-sql.md) (accepted policy), and
[`spec/sql/AGENTS.md`](../../spec/sql/AGENTS.md) (working rules). Where the brief speaks as of
0.2, this profile takes the 0.1 subset; §10 lists what is deferred.

## 1. Boundary

ODTS describes analytical transformations: what a model computes, its columns, and its
correctness constraints. It describes **intent**; compiler adapters own implementation.

- Orchestration — scheduling, retries, triggers, ordering — belongs to
  [ODOS](../ODOS/SPEC.md) and MUST NOT appear in an ODTS document.
- Statistical monitoring (freshness, volume, anomaly, schema drift) is observability, not
  correctness, and is outside 0.1 documents (`dq/` owns it).
- Dataset-interchange contracts belong to ODCS (`spec/contracts/`).
- Engine and vendor terms (`MergeTree`, `Delta`, `Iceberg`, engine names) MUST NOT appear in a
  portable document. Engine-specific SQL lives only under `_ext/<engine>/`.

## 2. Documents and versioning

An ODTS document is one SQL file: a header comment followed by exactly one SQL statement.

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
select ...
```

- The first header line MUST be `@odts <version>`. The version applies to the whole file;
  blocks MUST NOT carry independent versions (per ADR-0016, rejected — not merely deferred).
- One document defines one model. The model name SHOULD equal
  `<parent-directory>.<file-stem>` of the document's path.
- Documents are authored in the profile's authoring dialect (DuckDB for OGIP, declared once in
  project configuration — `SPEC_DIALECT`), never per file.

## 3. Header grammar

The header is line-oriented: one directive per line, name and value separated by whitespace.
Alignment is cosmetic and MUST NOT carry meaning. Nested YAML MUST NOT be used.

The 0.1 directive vocabulary is closed:

| Directive | Form | Status |
|---|---|---|
| `model` | `model  <layer>.<name>` | required |
| `kind` | `kind  table \| view` | required |
| `owner` | `owner  <owner-id>` | optional |
| `tags` | `tags  a, b, c` (comma-separated) | optional |
| `depends` | `depends  <model> [, <model>…]` | optional — assertion only (§4) |
| `columns:` | block (§5) | optional |
| `checks:` | block (§6) | optional |
| `imports:` | block (§7) | optional |

An unknown directive MUST fail compilation. There is no pass-through: a directive an adapter
would ignore is a portability leak, same closed-vocabulary rule as ODOS.

Semantic classification (entity · fact · dimension · history · snapshot · feature) is carried
in `tags` in 0.1; a dedicated `type` directive is deferred (§10).

## 4. Inference before authoring

A directive that can be computed MUST NOT be required, and when authored anyway it becomes an
assertion the compiler checks:

- **Engine/file type** (the `@bruin`-era `type: duckdb.sql`) is derived from the authoring
  dialect and file extension. It MUST NOT be authored.
- **`depends`** is derived from the SQL AST (`dialect.table_refs()`). When written, the
  compiler MUST fail if the declaration disagrees with the AST. A `depends` that merely
  repeats the AST SHOULD be omitted.

## 5. Columns

Compact table syntax, one column per line: `name  type  attribute*`. Simple attributes stay
inline; long metadata expands underneath as indented `namespace.key value` lines.

```
columns:
  game_sk      varchar   pk !null unique
  country_id   bigint    fk(core.country.id)
    fk.relationship   many-to-one
    fk.validation     warn
```

Core attribute vocabulary: `pk` · `bk` · `fk(<model>.<column>)` · `!null` · `unique` ·
`generated` · `deprecated` · `pii`.

Inline constraint attributes are named vendor-neutral checks with optional arguments —
`non_negative`, `between(0,5)` — drawn from the implementation's portable check vocabulary
(the names its adapters can all render; for OGIP today: `not_null` via `!null`, `unique`,
`non_negative`, `between`). An attribute outside the core vocabulary, the reserved namespaces,
and the check vocabulary MUST fail compilation.

Reserved namespaces for growth: `scd2.*` · `dv2.*` · `cdc.*` · `dq.*` · `metric.*` ·
`semantic.*` · `partition.*` · `cluster.*`. A namespace MUST NOT be populated before a model
needs it.

## 6. Checks

Simple constraints stay inline on the column (§5). Anything with a name or a cross-model
reference goes in `checks:` — one check per entry: a name and a vendor-neutral expression or
check-function call.

```
checks:
  title_not_blank   expression(trim(title) <> '')
  valid_fk          relationship(game_id -> core.game.game_id)
```

Checks are statements of correctness; adapters render them natively (dbt tests, Bruin checks,
SQLMesh audits). Monitors are not checks and MUST NOT appear here (§1).

## 7. Imports and macros

Macros are semantic operations, written `@ns.name(args)`. Namespaces are imported, never
global:

```
imports:
  odts.keys    as keys
  odts.dates   as dates
```

- Jinja MUST NOT appear in an ODTS document; it MAY exist only in generated projects.
- A macro is defined once in the registry and compiled natively per engine (SQLMesh `@DEF`,
  dbt/Bruin Jinja, plain-SQL expansion).
- Every macro MUST carry a conformance test: one fixture, run through every adapter on the
  authoring engine, asserting byte-identical output. No macro lands without one.
- A macro name that does not resolve in the registry MUST fail compilation.

## 8. SQL body

- Portable SQL in the authoring dialect; everything that must understand the SQL parses it
  (sqlglot) — string matching MUST NOT be used for reference rewriting or lineage.
- LValue projections use `:=` only (`sk := md5(id)`), desugared by the frontend when the
  `PropertyEQ` node is a **direct child of the projection list**; nested `:=` remains an
  engine named-argument. `=` as a projection alias MUST be rejected with an error pointing at
  `:=` — it parses as an equality predicate and yields a silently wrong boolean column.
- Pipe syntax (`|>`) MUST NOT appear in 0.1 documents (deferred, §10).
- References to other models use the model's dotted name (`staging.stg_games`) as a plain
  table reference; adapters rewrite them natively (`{{ ref(...) }}`, SQLMesh model refs)
  AST-scoped, never textually.

## 9. Compilation, IR, and conformance

The canonical model is the typed IR, never the header text:

```
spec/sql/**/*.sql (@odts) ──▶ frontend ──▶ rendered legacy YAML header ──▶ parse_asset() ──▶ Asset IR ──▶ adapters
```

For OGIP the frontend renders `@odts` into the legacy `@bruin` YAML header text
(required verbatim by one target), which feeds the unchanged `parse_asset()` pipeline and the
six adapters. The rendered YAML MUST NOT be committed. Both markers stay valid during
migration; the frontend dispatches on `/* @odts` vs `/* @bruin`.

A conforming implementation MUST test:

- **round-trip** — for every migrated model, the rendered legacy header is equivalent to the
  previous hand-written one;
- **depends assertion** — an authored `depends` contradicting the AST fails;
- **LValue** — `x = y` in a projection is rejected; `x := y` desugars, nested `:=` survives;
- **macro conformance** — byte-identical output per adapter (§7);
- **target regeneration** — all declared targets compile and committed generated output
  matches a fresh compile (`spec-compile` / `spec-verify`).

One formatter is canonical (sqlfluff for OGIP); a second formatter MUST NOT be introduced.
Formatting never changes semantics.

## 10. Deferred from 0.1

Deferred, with the brief as design authority — not accepted as extension syntax until a
version defines them: pipe syntax (`|>`, frontend-desugared) · a `sql` dialect/capability
directive · a semantic `type` directive · `materialize` strategies beyond `table`/`view`
(OTS vocabulary: `incremental` with `delete_insert`/`append`/`merge`, `scd2`) · `grain` /
`key` directives · a `doc`/`description` directive · `monitors:` and `metrics:` blocks ·
`include`. Per-block grammar versions are **rejected** by ADR-0016, not deferred.
