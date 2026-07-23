# ODOS — Open Data Orchestration Standard

This directory is OGIP's normative **ODOS 0.1 profile**, extracted from the approved
[ODOS design](../../docs/superpowers/specs/2026-07-20-odos-orchestration-spec-design.md).
ODOS describes when work runs, in what order, and how it survives failure. It does not describe
the transformations themselves.

Files:

- [`SPEC.md`](SPEC.md) — normative semantics and conformance requirements;
- [`schema.json`](schema.json) — closed-vocabulary JSON Schema for ODOS YAML;
- [`examples/`](examples/) — the six-group OGIP conformance model plus defaults;
- [`IMPLEMENTATION.md`](IMPLEMENTATION.md) — the OGIP implementation
  (`experimental/orchestration/dagster_ogip/` · `pipelines/flows/` · `src/ogip/tasks/`)
  described in the standard's terms.

The package is engine-independent and readable without Dagster or Prefect. The schema validates
document shape; compiler validation additionally resolves task names, asset selections,
cross-references, target capabilities, partitions, and the ODTS-derived asset graph.

Run `just standards-validate` to validate the schema and examples.
