# ADR-0005 — `spec/` as engine-agnostic SSoT: Bruin format + ODCS + compiler

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D0/D5 · [ADR-0004](ADR-0004-sqlmesh-default-transform-engine.md)

## Context

The engine is a choice, so the specification must not be bound to any one engine. We also
want lineage, DQ, ownership, and portable SQL to live in one readable place.

## Decision

`spec/` is the single source of truth. SQL is authored in **Bruin asset format** (SQL body +
`@bruin` YAML: `depends`→lineage, `columns[].checks`→DQ, `owner`/`tags`→metadata); source
contracts in **ODCS**. A small **spec compiler** (`src/ogip/spec_compile/`) renders spec →
engine-native projects (SQLMesh default; dbt/Bruin for comparison profiles). No engine binary
is required to *read* spec.

## Consequences

- One file per model expresses SQL + lineage + DQ + ownership; engines are swappable.
- Bruin authoring + SQLMesh runtime implies a compile step (accepted cost for the SSoT story).

## Alternatives considered

- **Author natively in SQLMesh** — drops the compiler but binds the spec to one engine.
- **Author in dbt** — rejected: "the next dbt" smell; weaker portability.
