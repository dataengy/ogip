# Open Transformation Specification (OTS) vs OGIP's `@odts`

**Question asked:** [OTS](https://github.com/francescomucio/open-transformation-specification)
states `@odts`'s problem almost word for word — *"define portable, executable data
transformations with a standard specification"*. Are we reinventing it? (Raised as F7 in
[.ai/FIXME.md](../../.ai/FIXME.md) and closed by this document; it gated
[#35](https://github.com/dataengy/ogip/issues/35).)

**Verdict: not a competitor — a different layer. Do not adopt as the authoring format; keep it
as a candidate *export target* and align vocabulary now, while alignment is still free.**

## What OTS is

An Apache-2.0 specification (v0.2.2) for describing SQL transformations as YAML/JSON so that
OTS-compliant tools can exchange them. It covers transformations, schema, materialization
(table · view · incremental with delete_insert/append/merge · SCD2), column- and table-level
tests, and — since 0.2.0 — user-defined functions. Reference implementation: *Tee for
Transform*.

## The decisive difference: interchange, not authoring

OTS stores SQL as a **string inside YAML**, and stores it three ways:

```yaml
code:
  sql:
    original_sql:  "SELECT id, name FROM source.customers WHERE active = true"
    resolved_sql:  "SELECT id, name FROM warehouse.source.customers WHERE active = true"
    source_tables: ["source.customers"]
```

Nobody hand-writes that. `resolved_sql` is `original_sql` with names qualified; `source_tables`
is derivable from either. All three must be kept in agreement, which is precisely the staleness
[ADR-0016](../adr/ADR-0016-odts-authoring-format-spec-sql.md) rules against with *"infer before
you require"*. This is a **compiled artifact** — something a tool emits.

`@odts` optimizes for the opposite end: a human or agent editing a file. SQL is a first-class
body, not a quoted string, which is what lets **sqlfluff lint it** and git diff it line by line.
Both properties disappear the moment SQL becomes a YAML scalar.

| | OTS | `@odts` |
|---|---|---|
| Written by | tools | humans and agents |
| SQL | string field ×3 (original / resolved / source_tables) | the file body |
| Lintable by sqlfluff | no | yes |
| Diff granularity | whole scalar | line |
| Redundancy | deliberate (self-contained payload) | rejected — inferred instead |

So the two do not compete. In ADR-0016's own pipeline — *authoring → typed AST → canonical IR →
compiler → target adapters* — `@odts` is the **first** box and OTS is a plausible **canonical
IR / export** shape.

## What we should take from it

**1. Align materialization vocabulary before we invent our own.** `@odts 0.1` has only
`table`/`view`. OGIP will need incremental and SCD2 (the `am_*` and history layers). OTS already
names them: `delete_insert` · `append` · `merge` · `scd2` with `start_column`/`end_column`, plus
`on_schema_change`. Adopting those names costs nothing today and avoids a gratuitous dialect
later.

**2. Align the test vocabulary.** OTS splits column-level vs table-level, and standard vs
generic-SQL vs singular-SQL tests, with `severity: error|warning`. `@odts`'s `checks:` block
covers the same ground and should use the same words.

**3. It independently validates the [#36](https://github.com/dataengy/ogip/issues/36) macro
design.** OTS `functions` carry `code.generic_sql` **plus** `code.database_specific` keyed by
database — one semantic definition, per-engine renderings. That is OGIP's macro registry,
arrived at separately. Worth noting that OTS does *not* specify how the two are kept consistent;
our conformance test is the part we should keep.

**4. `object_tags` vs `tags`.** OTS separates governance tags attached to database objects (PII,
classification) from selection/discovery tags. `@odts` has only `tags`. Useful distinction when
`pii` graduates from a column attribute to something the warehouse must carry.

## What we should not do

**Do not depend on it.** 40 stars, 0 forks, 17 commits, single maintainer, created 2025-10-27,
last pushed 2025-12-18, pre-1.0 with breaking changes across 0.1 → 0.2.2. Vocabulary alignment
is cheap and reversible; a runtime or format dependency is neither.

**Do not adopt it as the authoring format.** It would cost sqlfluff linting, line-level diffs,
and the inference rules — the three things `@odts` exists to provide.

## Naming note

OTS expands to *Open **Transformation** Specification*; ODTS expands to *Open **Data**
Transformation Standard*. The acronyms differ, so the project's
[YA-on-collision convention](../adr/ADR-0016-odts-authoring-format-spec-sql.md) does not fire —
but the expansions are one word apart, and both describe portable SQL transformations. Flagging
for the owner rather than acting: this is a judgement call about a name, not a defect.

## Follow-up

A `to_ots` adapter would make every OGIP model consumable by any OTS-compliant tool from the
same spec, at the cost of one more generator. Not scheduled — recorded here so the option is
not rediscovered from scratch.
