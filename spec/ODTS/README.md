# ODTS — Open Data Transformation Standard

This directory is OGIP's normative **ODTS 0.1 profile**. ODTS describes what a transformation
computes — its model, columns, and correctness constraints. It does not describe when work
runs (that is [ODOS](../ODOS/README.md)) or dataset interchange (that is ODCS,
`spec/contracts/`).

Files:

- [`SPEC.md`](SPEC.md) — normative grammar, semantics, and conformance requirements;
- [`GOVERNING-BRIEF.md`](GOVERNING-BRIEF.md) — the standard-owner's design brief, verbatim
  (the governing document; the 0.1 profile is its OGIP-scoped subset);
- [`examples/`](examples/README.md) — the four `spec/sql` models re-authored as `@odts 0.1`
  conformance fixtures, bodies byte-identical to the live SQL;
- [`IMPLEMENTATION.md`](IMPLEMENTATION.md) — the OGIP implementation (`spec/sql` ·
  `src/ogip/spec_compile` · `transform/`) described in the standard's terms.

Extraction history: this package was deliberately held back as a readiness record while
ADR-0016 fixed policy but no governing document defined the grammar surfaces
([ADR-0017](../../docs/adr/ADR-0017-odos-normative-profile.md) records that state). The
governing brief's arrival unblocked it —
[ADR-0018](../../docs/adr/ADR-0018-odts-normative-profile.md) records the extraction and its
honest limits: the live `spec/sql` files stay on the legacy `@bruin` header until the `@odts`
frontend lands ([#35](https://github.com/dataengy/ogip/issues/35)); the macro registry is
[#36](https://github.com/dataengy/ogip/issues/36).

The package is engine-independent and readable without any engine binary. Schema-level
validation here covers the fixtures; frontend validation (depends assertion, LValue rules,
macro resolution) is compiler work tracked in the issues above.

Run `just standards-validate` to validate both standards packages and their examples.
