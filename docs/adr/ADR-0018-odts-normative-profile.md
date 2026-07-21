# ADR-0018 — ODTS 0.1 normative transformation profile

- **Status:** Accepted
- **Date:** 2026-07-22
- **Relates to:** [ADR-0016](ADR-0016-odts-authoring-format-spec-sql.md) ·
  [ADR-0017](ADR-0017-odos-normative-profile.md) ·
  [governing brief](../../spec/ODTS/GOVERNING-BRIEF.md)

## Context

ADR-0017 published the ODOS package but explicitly blocked a `spec/ODTS` package: ADR-0016
fixes ODTS *policy* (versioning, macros, Jinja ban, LValue, formatter, the six targets), yet by
itself defines neither the header directive grammar nor column/check/import syntax nor the IR
mapping. `spec/ODTS/README.md` was a readiness record, and a test
(`test_standard_packages.py`) locked that state so nobody could publish a spec that invented
syntax.

The blocker was the absence of a **governing document**. On 2026-07-22 the standard owner
supplied one — the ODTS design brief, now recorded verbatim in
`spec/ODTS/GOVERNING-BRIEF.md`. Together with ADR-0016's accepted policy and the working
grammar in `spec/sql/AGENTS.md`, every 0.1 construct now has a source of authority; nothing in
a published profile needs inventing.

## Decision

Adopt the [ODTS 0.1 normative profile](../../spec/ODTS/README.md) with:

- normative grammar, semantics, and conformance requirements in `spec/ODTS/SPEC.md`, scoped to
  the constructs the OGIP implementation actually needs — the brief's 0.2-level constructs
  (pipe, `sql` directive, `monitors:`, `metrics:`, materialization strategies, `doc`) are
  listed as deferred, not silently included;
- the governing brief preserved verbatim as `GOVERNING-BRIEF.md` with provenance;
- conformance fixtures in `examples/` mirroring the four live `spec/sql` models with
  **byte-identical SQL bodies**, so fixtures cannot drift from the SSoT unnoticed;
- deterministic tests replacing the extraction lock: closed directive vocabulary, required
  directives, model-name/path agreement, and fixture-body identity with `spec/sql`.

The name stays **ODTS**: per ADR-0016's convention only a colliding name takes `YA`, and ODTS
was checked and is unclaimed (the umbrella remains YADPS). No `YADTS` rename.

Publication changes no runtime behaviour. The live `spec/sql` documents keep their legacy
`@bruin` headers until the `@odts` frontend lands (#35); the macro registry remains #36. The
profile describes the format those tasks implement — it does not claim they are done.

## Consequences

- ODTS 0.1 has a reviewable, machine-validatable package alongside ODOS; the standards family
  (YADPS · ODTS · ODOS) is now fully extracted at matching levels.
- The "not yet extractable" lock in `test_standard_packages.py` is replaced by positive
  conformance tests; `just standards-validate` covers both packages.
- Fixture-body identity makes every future `spec/sql` edit fail the standards gate until the
  fixture is updated — the drift alarm is structural, not procedural.
- Honest limits stay recorded in the package README: frontend (#35), macros (#36), and the
  frontend-level validations (depends assertion, LValue rules) are still compiler work.
