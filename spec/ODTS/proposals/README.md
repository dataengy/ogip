# ODTS proposals

Pre-normative design input for ODTS versions after [0.1](../SPEC.md). Everything here is a
**proposal**: not accepted, not normative, and not something an adapter may implement.

The authority ranking is unchanged — [GOVERNING-BRIEF.md](../GOVERNING-BRIEF.md) is the design
authority, [SPEC.md](../SPEC.md) is the accepted 0.1 profile, and an
[ADR](../../../docs/adr/) records acceptance. A document in this directory has cleared none of
those gates; it exists so that a syntax idea is evaluated in writing instead of surviving as an
untracked scratch file, and so that a rejection is recorded once rather than re-argued.

## Not conformance examples

[`../examples/`](../examples/) holds the 0.1 conformance fixtures, globbed as
`spec/ODTS/examples/*/*.sql` by `src/tests/unit/test_standard_packages.py` and asserted against
the live `spec/sql` models. **This directory is deliberately outside that glob**, and proposals
are written as Markdown with any sketch in a fenced block — a stray `.sql` file under
`examples/` fails three tests at once (fixture count, closed vocabulary, body identity), which
is exactly how the first document here was found.

Put a draft here, or in `.tmp/` if it is scratch. Never in `examples/`.

## Required form

The brief's `OUTPUT STYLE` section governs: every proposal carries **motivation · grammar ·
examples · IR mapping · compiler implications · backward compatibility · tradeoffs**, and
records the source it evaluates verbatim. Per-element verdicts are explicit — a proposal is
normally part-accepted, and the rejected parts are the ones most worth writing down.

The load-bearing section is **IR mapping**. [SPEC.md §9](../SPEC.md) makes the typed IR
canonical, never the header text, so a proposal that leaves the IR unchanged is a frontend
concern and cheap; one that changes it reaches all six adapters and needs an ADR.

## Contents

| Proposal | Subject | Status |
|---|---|---|
| [0.2-compact-projection.md](0.2-compact-projection.md) | Shared header fragments, projection-carried column metadata, `::`/`?` casts, macro files | part carry-forward, part rejected |
