      # `.ai/FIXME.md` — known conflicts and debt, high priority

Problems that are **real but not yet fixed** — contradictions between documents, convention
gaps, and debt that a passing agent should not silently step over. Distinct from
[TODO.md](TODO.md) (near-term actions) and [tasks/](tasks/) (scoped work with an issue):
an entry lives here until it is either fixed inline or graduates into a task file.

**Rules.** Every entry names the *failure*, not just the file. An entry that becomes wrong is
deleted, not left as archaeology. Do not "fix" anything marked **DO NOT TOUCH**.

**Scheduled closures (finalization run 2026-07-30,
[plan](../docs/superpowers/plans/2026-07-30-finalization-land-everything.md)):** F8 closed
2026-07-30 (no `ODPS` survives — row deleted per the register's own rule) · F4 closed
2026-07-30 (all six READMEs exist — row deleted) · F6 fixed 2026-07-30 (tasks-sync realigned
#19's body). **F1 and F2 stay open together** — both are the *authoring format* flip and move
atomically with [#35](https://github.com/dataengy/ogip/issues/35) (rule 2 + the 10-document
sweep belong in the same commit as the first `@odts` model; a half-sweep now would just create
a second drift). F3/F5 stay owner-decisions — untouched.

| # | Problem | Severity | Wrong when | Owner lane |
|---|---|---|---|---|
| [F1](#f1--hard-rule-2-contradicts-adr-0016) | Hard rule 2 contradicts ADR-0016 | **P1** | when [#35](https://github.com/dataengy/ogip/issues/35) lands | `spec` |
| [F2](#f2--format-claims-scattered-across-10-documents) | "Bruin asset format" asserted in 10 documents | **P1** | when [#35](https://github.com/dataengy/ogip/issues/35) lands | `spec` |
| [F3](#f3--adr-0005-has-no-forward-pointer) | ADR-0005 has no forward pointer to ADR-0016 | P2 | **now** | `spec` |
| [F5](#f5--semantic-layer-format-is-undecided-against-odts) | Semantic-layer format undecided against `@odts` | P3 | when [#20](https://github.com/dataengy/ogip/issues/20) starts | `spec` |

_F7 (ODTS vs the Open Transformation Specification) was evaluated and closed — verdict in
[docs/comparisons/ots-vs-odts.md](../docs/comparisons/ots-vs-odts.md); the alignment work it
produced lives on [#35](https://github.com/dataengy/ogip/issues/35) and
[#36](https://github.com/dataengy/ogip/issues/36)._

## F1 — hard rule 2 contradicts ADR-0016

[AGENTS.md](AGENTS.md) hard rule 2 states: *"SQL is authored in **Bruin asset format**"*.
[ADR-0016](../docs/adr/ADR-0016-odts-authoring-format-spec-sql.md) is **Accepted** and says
`@odts 0.1`. Project law and an accepted decision record disagree.

**Not wrong today** — every model in `spec/sql` is still `@bruin`, so the rule describes
reality. It becomes wrong the moment the first `@odts` file lands, and hard rule 2 is exactly
the line an agent reads before touching `spec/`. A stale hard rule is worse than a stale
README: it is *obeyed*.

**Fix:** part of [#35](https://github.com/dataengy/ogip/issues/35) — see
[tasks/spec-compact-header.md](tasks/spec-compact-header.md). Rule 2 must move in the same
commit as the first converted model, not after.

## F2 — format claims scattered across 10 documents

Ten documents independently assert the authoring format. None derives it from ADR-0005, so
each must be edited by hand when `@odts` lands, and any missed one silently misleads.

| File | Line | Note |
|---|---|---|
| [AGENTS.md](AGENTS.md) | 41 | hard rule 2 — see [F1](#f1--hard-rule-2-contradicts-adr-0016) |
| [PLAN.md](PLAN.md) | 73, 423 | narrative + decision D0 |
| [STATUS.md](STATUS.md) | 192 | decision D0 |
| [CLAUDE.md](CLAUDE.md) | 44 | key-paths line |
| [../README.md](../README.md) | 47 | public front page |
| [../docs/architecture/overview.md](../docs/architecture/overview.md) | 40 | ⚠ **dirty in another lane** — hand off, do not edit |
| [../docs/ROADMAP.md](../docs/ROADMAP.md) | 15 | ⚠ **dirty in another lane** — hand off, do not edit |
| [../docs/comparisons/dagster-odp-vs-spec-compiler.md](../docs/comparisons/dagster-odp-vs-spec-compiler.md) | 28 | comparison table |
| [../transform/README.md](../transform/README.md) | 3 | + `../transform/runner.py:3` |
| `../src/ogip/spec_compile/*.py` | docstrings | `__init__`, `bruin`, `to_dbt`, `to_sqlmesh`, `to_bruin` |

**DO NOT TOUCH:** [../docs/CHANGELOG.md](../docs/CHANGELOG.md) lines 22 and 37. A changelog
records what was true at the time; "correcting" history is the bug, not the fix.

**Fix:** checklist lives in [tasks/spec-compact-header.md](tasks/spec-compact-header.md).

## F3 — ADR-0005 has no forward pointer

[ADR-0005](../docs/adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md) is `Accepted` and still
reads as the current format decision. [ADR-0016](../docs/adr/ADR-0016-odts-authoring-format-spec-sql.md)
references *it*, satisfying the letter of the convention in
[docs/adr/README.md](../docs/adr/README.md) — but a reader landing on 0005 has no way to learn
it was refined.

**The gap is in the convention, not the file.** `docs/adr/README.md` says ADRs are *"immutable
once Accepted"* and that supersession is recorded on the **new** ADR. It has no notion of
*partial* refinement: ADR-0016 replaces 0005's format detail while leaving its SSoT-and-compiler
decision fully in force, so "Superseded" is too strong and silence is too weak.

**Needs an owner decision**, one of: (a) allow a `Refined by:` header line on an Accepted ADR
and amend the convention to permit it; (b) accept forward-pointer silence as the cost of
immutability; (c) supersede 0005 wholesale with a re-statement. Do not resolve this unilaterally
— it changes how every future ADR is written.


## F5 — semantic-layer format is undecided against `@odts`

[tasks/spec-semantic-layer.md](tasks/spec-semantic-layer.md) ([#20](https://github.com/dataengy/ogip/issues/20))
plans semantic definitions in **Bruin Semantic Layer** YAML. `@odts` covers `spec/sql` only, so
the two do not collide today — but landing `@odts` while #20 adds a second Bruin-format surface
re-opens the same vendor-marker argument ADR-0016 just settled.

**Decide before #20 starts:** does the semantic layer follow `@odts`, stay Bruin YAML as a
deliberate exception, or become plain YAML with no vendor marker? Cheap now, expensive after
the definitions exist.
