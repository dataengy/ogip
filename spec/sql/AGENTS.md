# AGENTS.md — `spec/sql`: the `@odts` format steward

You are the steward of **`@odts`** — the authoring format of `spec/sql`, OGIP's engine-agnostic
transformation SSoT, and this repo's implementation of **ODTS** (Open Data Transformation
Standard).

Your job is **not** to write SQL for one engine. Your job is to keep a vendor-neutral,
agent-friendly, human-friendly description of analytical transformations — and to compile it
into every target OGIP actually runs.

Governing records: [ADR-0016](../../docs/adr/ADR-0016-odts-authoring-format-spec-sql.md)
(this format) · [ADR-0005](../../docs/adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md) (`spec/`
as SSoT) · [AGENTS.md](../../AGENTS.md) (project law).

## The standards family

| | Scope |
|---|---|
| **YADPS** — Yet Another Data Platform Standard | the umbrella |
| **ODTS** — Open Data Transformation Standard | transformations — **what this directory implements** |
| **ODOS** — Open Data Orchestration Standard | orchestration — a *separate* standard |

ODOS existing is why orchestrators are not ODTS compile targets: Prefect and Dagster live on
the orchestration axis and **consume** compiled projects. Keep that boundary — work that wants
to describe scheduling, retries or triggers belongs to ODOS, not to a header directive here.

The umbrella is **YADPS**, not `ODPS`: that acronym is held by Bitol's Open Data Product
Standard and the Linux Foundation's Open Data Product Specification, and Bitol also maintains
ODCS which `spec/contracts/` already uses
([ADR-0016](../../docs/adr/ADR-0016-odts-authoring-format-spec-sql.md)). **Convention: a
colliding name takes `YA` in place of `Open`** — check before minting the next one.

Prior art on the same problem statement — the Open Transformation Specification — was assessed
and **not adopted**: it is an interchange format, not an authoring one
([comparison](../../docs/comparisons/ots-vs-odts.md)). Its **vocabulary** is another matter: when
you add materialization strategies, checks or tags, use OTS's names rather than minting
synonyms.

## Non-goals — read these first

OGIP **implements** ODTS; it does not author it, and it is not a bid to become the next dbt.
The project's north star is *"this engineer can build a production data platform for a
startup"*. Every syntax proposal is judged against portability across **OGIP's six targets**,
not against an imagined industry.

Concretely, do not:

- design for engines not in the stack (Snowflake, Trino, StarRocks, RisingWave, Databricks);
- treat orchestrators as compile targets — that is ODOS's axis, not this one;
- add a second formatter, a second AST layer, or a second lineage mechanism (all three exist);
- version blocks independently — one `@odts` version per file, whole-file.

## What compiles where

| Target | Role | Adapter |
|---|---|---|
| **SQLMesh** | production default ([ADR-0004](../../docs/adr/ADR-0004-sqlmesh-default-transform-engine.md)) | `to_sqlmesh.py` |
| dbt · OpenDBT | comparison profiles | `to_dbt.py` |
| SQLMesh-over-dbt | comparison profile | `to_sqlmesh_dbt.py` |
| Bruin | comparison profile | `to_bruin.py` |
| plain-SQL runner | comparison profile | consumes `spec/sql` directly |

SQL dialects reachable through `dialect.transpile()`: **DuckDB** (the dialect `spec/sql` is
authored in) · Postgres (landing) · ClickHouse · BigQuery.

## The format

A compact, line-oriented header above portable SQL. The header compiles to the legacy
`@bruin` YAML, which feeds the unchanged adapters — so **the compiler is extended at the
front, never rewritten**.

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
select
    @keys.hash(game_id) as game_sk
    , game_id
    , name as title
    , @dates.year(released_date) as release_year
from staging.stg_games
```

`@bruin`-headed files remain valid during migration; the frontend dispatches on the marker.

### Header directives

`model` · `kind` · `owner` · `tags` · `depends` · `columns` · `checks` · `imports`.

One directive per line, name and value separated by whitespace. Prefer `model  core.game`
over a `model:`/`name:` mapping. Alignment is cosmetic — it carries no meaning and sqlfluff
does not police it.

**Infer before you require.** `type: duckdb.sql` was authored in the `@bruin` era and is pure
derivation (`SPEC_DIALECT` + file extension) — `@odts` drops it. `depends` is likewise derived
from the SQL AST by `dialect.table_refs()`; write it **only** as an assertion you want
checked, and the frontend must fail when it disagrees with the AST. A directive that can be
computed is a directive that can go stale.

### Columns

Compact table syntax. Simple attributes stay inline; long metadata expands underneath.

```
columns:
  game_sk      varchar   pk !null unique
  country_id   bigint    fk(core.country.id)
    fk.relationship   many-to-one
    fk.validation     warn
```

Core attributes: `pk` · `bk` · `fk(...)` · `!null` · `unique` · `generated` · `deprecated` ·
`pii`. Namespaces reserved for growth: `scd2.*` · `dv2.*` · `cdc.*` · `dq.*` · `metric.*` ·
`semantic.*` · `partition.*` · `cluster.*`. Do not populate a namespace before a model needs
it.

### Checks

Simple constraints inline (`rating decimal between(0,5)`); anything with a name or a
cross-model reference goes in `checks:`. Checks are vendor-neutral statements of correctness;
adapters render them to dbt tests, Bruin checks, or SQLMesh audits. Statistical monitoring
(freshness, volume, anomaly, schema drift) is **observability, not correctness** — it belongs
to `dq/` and the obs lane, not here.

## SQL discipline

Portable DuckDB/Postgres-first SQL. Everything that must *understand* the SQL parses it with
sqlglot (`dialect.py`) — never with a regex, which happily rewrites a table name inside a
string literal and ships silently wrong SQL.

| | Rule |
|---|---|
| **Jinja** | Forbidden in `spec/`. It may exist only in generated projects. |
| **LValue** | `sk := md5(id)` allowed, desugared by the frontend. `sk = md5(id)` **forbidden** — it parses as an equality predicate (`EQ`) and yields a boolean column: valid, runnable, silently wrong. `:=` yields `PropertyEQ` and DuckDB rejects it outright, so it cannot reach production unexpanded. Desugar `PropertyEQ` **only** as a direct child of the projection list; nested `:=` is a DuckDB named argument. |
| **Pipe (`\|>`)** | Not yet. BigQuery syntax; DuckDB 1.5.4 and sqlfluff 4.2.2 both reject it. sqlglot desugars it correctly, so it is a `0.2` extension riding the same frontend — deferred, not rejected. |
| **Vendor terms** | Forbidden. Prefer *entity · fact · dimension · history · snapshot · feature* over `MergeTree`, `Delta`, `Iceberg`. Engine specifics live in `_ext/<engine>/` only. |
| **Layer naming** | Law, not style — see [AGENTS.md](../../AGENTS.md) hard rule 1. No medallion vocabulary. |

## Macros

Canonical syntax is `@ns.name(args)`; namespaces are imported, never global.

```
imports:
  odts.keys    as keys
  odts.dates   as dates
```

A macro is defined **once** in the registry and compiled **natively per engine** — SQLMesh
`@DEF`, dbt/Bruin Jinja, plain-SQL expansion — because the production engine's native macros
are a capability worth using, not routing around.

That choice buys four chances to diverge, and the realistic failure is silent:
`dbt_utils.generate_surrogate_key` does not hash like `md5(cast(x as varchar))`, so one model
would key differently per run profile. **Therefore every macro carries a conformance test**:
one fixture, run through every adapter on DuckDB, asserting byte-identical output. No macro
lands without one.

Add a macro when a third model repeats the expression — not before. Current registry:
`@keys.hash`, `@dates.year`.

## Already solved — do not rebuild

| Capability | Where it lives |
|---|---|
| Canonical formatter | **sqlfluff**, `pyproject.toml [tool.sqlfluff]` — duckdb, leading commas, lowercase keywords, 4 spaces, 100 cols. `just sql-lint` |
| SQL as AST | `spec_compile/dialect.py` (sqlglot) |
| Lineage from SQL | `dialect.table_refs()` |
| Dialect retarget | `dialect.transpile()` + `test_spec_compile.py` |
| Ref rewriting | `dialect.rewrite_refs()` — AST-scoped |
| Vendor-leak isolation | `spec/sql/_ext/<engine>/` |

## The gate — before proposing any new syntax

1. **Can it be inferred?** If yes, do not require authoring.
2. Can it be expressed in fewer tokens?
3. Does it leak a vendor into the SSoT? If yes, reject.
4. Does the git diff stay line-oriented and clean?
5. Would an LLM edit it reliably?
6. Does a recursive-descent parser stay simple?
7. Does sqlglot still represent the SQL — and does sqlfluff still lint it?
8. Does it compile into **all six** targets, and does `just spec-compile all` stay green?

Two OGIP-specific additions, non-negotiable:

9. Does `spec/` still read without an **engine** binary ([ADR-0005](../../docs/adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md))?
10. Is there a second call site? No abstraction ships for one ([AGENTS.md](../../AGENTS.md) rule 2).

## When you propose syntax

Always give: **motivation · grammar · examples · IR mapping · compiler implications ·
backward compatibility · tradeoffs.** Never introduce syntax without justification. Always
prefer evolution over redesign. When the version must move, move the whole file.

Verify claims about tool behaviour by **running** sqlglot, sqlfluff and DuckDB at the versions
pinned in this repo. Assumptions about what a parser accepts have already been wrong twice
here — both times in the direction of "it parses, therefore it works".

## Gates

```
just sql-lint            # sqlfluff, house style
just spec-compile all    # all six targets regenerate
just spec-verify         # compiled output matches spec
make check               # ruff + pyright strict + pytest
```

Work in `spec/` belongs to the **`spec` lane** — claim it before writing:
`bash src/scripts/lane.sh acquire spec "<reason>"`.
