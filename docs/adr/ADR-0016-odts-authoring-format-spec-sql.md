# ADR-0016 — `@odts` authoring format for `spec/sql`: compact header, macros, SQL discipline

- **Status:** Accepted
- **Date:** 2026-07-20
- **Relates to:** D0/D5 · [ADR-0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md) · [ADR-0004](ADR-0004-sqlmesh-default-transform-engine.md) · [ADR-0001](ADR-0001-edw-layering-no-medallion.md)

## Context

[ADR-0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md) made `spec/` the SSoT and fixed the
authoring format as **Bruin asset** (`/* @bruin <yaml> @bruin */` + SQL). Three pressures have
accumulated against it:

1. **Verbosity.** `spec/sql/core/game.sql` spends 16 header lines on metadata for a 12-line
   model. The header is the part agents edit most, and nested YAML costs tokens, invites
   indentation errors, and produces noisy diffs on one-attribute changes.
2. **A vendor name inside the vendor-neutral SSoT.** `@bruin` marks the SSoT with the name of
   one of six targets — the exact coupling ADR-0005 exists to prevent. Bruin is an authoring
   *serialization* here, never a production dependency, but the marker reads otherwise.
3. **No macro layer.** The surrogate key is hand-written (`md5(cast(game_id as varchar))`).
   The default engine, SQLMesh, has native `@` macros; that expressiveness is unused.

There is also no written policy on what may *enter* the format, so every proposal —
alternative SQL syntaxes, per-block versioning, semantic attributes — gets re-litigated from
scratch.

## Decision

Introduce **`@odts 0.1`**, a compact line-oriented header for `spec/sql`, and record the policy
governing its evolution.

`@odts` is OGIP's **implementation** of **ODTS** (Open Data Transformation Standard), which sits
under the **ODPS** (Open Data Platform Standard) umbrella alongside **ODOS** (Open Data
Orchestration Standard). OGIP conforms to the standard; it does not author it. That split is
load-bearing here — ODOS owning orchestration is precisely why Prefect and Dagster are **not**
ODTS compile targets in this repo but consumers of compiled projects.

⚠ The **ODPS** name collides with two public standards in OGIP's own ecosystem — Bitol's
[Open Data Product Standard](https://bitol-io.github.io/open-data-product-standard/v1.0.0/) and
the Linux Foundation's [Open Data Product Specification](https://opendataproducts.org/). Bitol
also maintains **ODCS**, which `spec/contracts/` already uses, so a reader will reasonably
assume ODPS is Bitol's too. Registered as [F7](../../.ai/FIXME.md#f7--odps-name-collides-with-two-public-standards);
it does not block this record, which concerns ODTS only.

**Compilation is front-loaded, not rebuilt.** A frontend in `src/ogip/spec_compile/` renders
`@odts` into the existing `@bruin` YAML header; `parse_asset()` and every adapter
(`to_sqlmesh` · `to_dbt` · `to_bruin` · `to_sqlmesh_dbt`) stay unchanged.

```
spec/sql/**/*.sql  (@odts, SSoT)  ──▶  rendered @bruin YAML  ──▶  parse_asset() ──▶ adapters
```

The rendered YAML is **never committed** — one copy, no drift. `@bruin` remains readable
during migration; the frontend dispatches on the marker.

Policy, in force from this record:

| Rule | Decision |
|---|---|
| **Format versioning** | One version per file (`@odts 0.1`). No per-block versions — they buy independent evolution at the price of a compatibility matrix we would have to test. |
| **Macros** | Allowed as `@ns.name(args)`, defined once in a registry, compiled **natively per engine** (SQLMesh `@DEF` · dbt/Bruin Jinja · plain-SQL expansion). Divergent implementations of one semantic are guarded by conformance tests (below). |
| **Jinja in `spec/`** | Forbidden. Jinja may only appear in *generated* projects. |
| **LValue projections** | Allowed via `:=` only (`sk := md5(id)`), desugared by the frontend. Never `=`. |
| **Pipe syntax** | Deferred to `@odts 0.2`; not rejected. |
| **Vendor terms** | Forbidden in `spec/` (`MergeTree`, `Delta`, `Iceberg`, engine names). Engine specifics live in `spec/sql/_ext/<engine>/` only. |
| **Formatter** | The existing **sqlfluff** config (`pyproject.toml [tool.sqlfluff]`) is canonical. No second formatter. |
| **Compile targets** | The six real ones: `sqlmesh` · `dbt` · `opendbt` · `sqlmesh-dbt` · `bruin` · plain-SQL runner. Orchestrators are **not** compile targets — they consume compiled projects. |

### Why `=` is forbidden and `:=` is not

Both parse. They do not mean the same thing, and only one fails loudly — verified on the
versions pinned in this repo (sqlglot 30.8.0, DuckDB 1.5.4, sqlfluff 4.2.2):

| Written | sqlglot node | DuckDB |
|---|---|---|
| `select name = title` | `EQ` — an equality **predicate**, yielding a boolean column | executes, silently wrong |
| `select name := title` | `PropertyEQ` — a distinct node | `Parser Error`, fails loudly |
| `list_value(a := 1)` | named argument, nested | executes correctly |

`=` is the dangerous class of syntax: valid, runnable, and quietly not what the author meant.
`:=` is unambiguous to the parser and rejected by the engine, so it cannot reach production
unexpanded. The frontend desugars `PropertyEQ` **only as a direct child of the projection
list** — nested `:=` stays a DuckDB named argument.

### Why pipe syntax is deferred rather than rejected

`|>` is BigQuery syntax, not DuckDB. DuckDB 1.5.4 rejects it and sqlfluff 4.2.2 cannot parse
it — so it cannot be authored today. But sqlglot desugars it correctly into a CTE with
lineage intact, which means the same frontend that expands `@odts` headers can expand pipe
before either tool ever sees it. It is a `0.2` extension with a known implementation path.

### Macro conformance

Compiling one macro to four native implementations is four chances to diverge — and the
realistic failure is silent: `dbt_utils.generate_surrogate_key` does not produce the same
hash as `md5(cast(x as varchar))`, so the same model would key differently per run profile.
Therefore every macro carries a **conformance test**: one fixture, executed through every
adapter on DuckDB, asserting byte-identical output. Divergence is CI-red, not a data
incident discovered downstream.

## Consequences

- Headers shrink roughly by half; diffs become line-oriented and agent-editable.
- The SSoT no longer carries a target's name.
- `spec/` still reads without any **engine** binary (ADR-0005's invariant); it now needs
  OGIP's own frontend parser, which is plain Python in this repo — not an engine dependency.
- We own a parser and a macro registry. That is a real maintenance surface, accepted because
  the alternative (hand-written vendor macros per engine) has a worse failure mode.
- Two header formats coexist during migration; the frontend must dispatch on the marker until
  the last `@bruin` file is converted.

## Alternatives considered

- **Keep `@bruin` YAML unchanged** — zero cost, but leaves the verbosity and the vendor
  marker in the SSoT, and never gets a macro layer.
- **Compile `@odts` straight to the `Asset` dataclass**, skipping YAML — thinner, but
  `to_bruin` copies files verbatim and would still need real `@bruin` text. The intermediate
  render is required by an existing target, so hiding it buys nothing.
- **Expand macros to native SQL for all targets, including SQLMesh** — one execution path and
  no drift risk, but discards SQLMesh's native `@` macros, a capability of the production
  engine. Rejected in favour of native mapping plus conformance tests.
- **Per-block grammar versions** (`columns(0.2 patch infer:sql)`) — independent evolution, at
  the cost of a version compatibility matrix. Rejected as complexity without a call site.
- **Authoring the standard rather than implementing it** — driving ODTS itself from this repo
  is out of scope by [AGENTS.md](../../AGENTS.md): the north star is a production platform,
  *not* "the next dbt". OGIP contributes a conforming implementation; `@odts`'s in-repo
  ambition is portability across OGIP's six targets, and syntax proposals are judged against
  those, not against an imagined industry.
