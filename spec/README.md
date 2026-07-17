# `spec/` — engine-agnostic Data Specification (SSoT)

The implementation-agnostic specification layer — *Open Data Contracts + portable SQL*
([ADR-0005](../docs/adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md)). Execution engines
**consume** this; they never redefine it. No engine binary is required to *read* `spec/`.

| Subdir | Holds | Format |
|---|---|---|
| `contracts/<source>/` | source data contracts (schema · quality · SLA · ownership) | **ODCS** |
| `sql/{staging,core,star,am,marts,fs}/` | portable SQL models (SQL + inline lineage/DQ/ownership) | **Bruin asset** format |
| `sql/_ext/<engine>/` | rare engine-specific SQL overrides | engine SQL |
| `dq/policy.yml` | cross-cutting DQ rules/severity | YAML |
| `datasets/` | dataset registry (metadata, ownership) | YAML |
| `lineage/` | derived dependency graph | generated |

The **spec compiler** (`src/ogip/spec_compile/`) renders these to engine-native projects —
**SQLMesh** (default), dbt, Bruin. _Populated in Phase 1; M0 seeds the first RAWG models._
