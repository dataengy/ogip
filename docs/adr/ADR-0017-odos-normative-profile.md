# ADR-0017 — ODOS 0.1 normative orchestration profile

- **Status:** Accepted
- **Date:** 2026-07-21
- **Relates to:** [ADR-0016](ADR-0016-odts-authoring-format-spec-sql.md) ·
  [ODOS design](../superpowers/specs/2026-07-20-odos-orchestration-spec-design.md)

## Context

The ODOS design defines a complete closed orchestration vocabulary, a two-target capability
matrix, failure policy, compiler boundary, and a six-group conformance model. Leaving it only as
a design document makes conformance non-machine-readable and allows Dagster and Prefect
orchestration to drift independently.

ODOS is the orchestration sibling of ODTS under the **YADPS** umbrella. ODTS describes what a
transformation computes; ODOS describes when work runs, in what order, and how it survives
failure. Neither standard embeds the other.

ADR-0016, by contrast, fixes ODTS policy but does not contain the complete header grammar. The
two standards are therefore ready for extraction at different levels.

## Decision

Adopt the [ODOS 0.1 normative profile](../../spec/ODOS/README.md) with:

- normative semantics and conformance requirements in `spec/ODOS/SPEC.md`;
- a Draft 2020-12 JSON Schema with a closed key vocabulary;
- shared defaults and six group examples covering the complete design model;
- deterministic tests for schema validity, group coverage, local references, unknown-key
  rejection, and explicit target restriction for non-portable hooks.

Uppercase `spec/ODOS/` describes the standard. The future lowercase
`spec/orchestration/` contains OGIP's live conforming documents and remains the input to the
planned Dagster and Prefect adapters. Examples under the standard package are conformance
fixtures, not a second runtime SSoT.

ODOS documents use YAML 1.2 semantics. The `"on"` key is quoted in portable examples because
YAML 1.1-compatible loaders otherwise coerce it to boolean `true` before schema validation.

Schema validation covers serialization shape. The compiler remains responsible for semantic
checks that JSON Schema cannot perform: registry lookup, asset-graph selection, cross-document
references, partition compatibility, target capability, and adapter equivalence.

Do not publish a complete `spec/ODTS/0.1` from ADR-0016 alone. `spec/ODTS/README.md` records the
missing grammar surfaces until a governing document defines them.

## Consequences

- ODOS 0.1 now has a reviewable, machine-validatable contract independent of either orchestrator.
- Unknown extension keys fail before projection, preserving the portability guarantee.
- The six-group example becomes the acceptance fixture for the future compiler.
- Live ODOS documents and adapters are still implementation work; this decision does not claim
  that Dagster or Prefect output is generated yet.
- ODTS extraction stays honest: policy is accepted, but conformance cannot be claimed until the
  complete grammar and IR mapping exist.
