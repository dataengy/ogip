      # `.ai/FIXME.md` — known conflicts and debt, high priority

Problems that are **real but not yet fixed** — contradictions between documents, convention
gaps, and debt that a passing agent should not silently step over. Distinct from
[TODO.md](TODO.md) (near-term actions) and [tasks/](tasks/) (scoped work with an issue):
an entry lives here until it is either fixed inline or graduates into a task file.

**Rules.** Every entry names the *failure*, not just the file. An entry that becomes wrong is
deleted, not left as archaeology. Do not "fix" anything marked **DO NOT TOUCH**.

| # | Problem | Severity | Wrong when | Owner lane |
|---|---|---|---|---|
| [F1](#f1--hard-rule-2-contradicts-adr-0016) | Hard rule 2 contradicts ADR-0016 | **P1** | when [#35](https://github.com/dataengy/ogip/issues/35) lands | `spec` |
| [F2](#f2--format-claims-scattered-across-10-documents) | "Bruin asset format" asserted in 10 documents | **P1** | when [#35](https://github.com/dataengy/ogip/issues/35) lands | `spec` |
| [F3](#f3--adr-0005-has-no-forward-pointer) | ADR-0005 has no forward pointer to ADR-0016 | P2 | **now** | `spec` |
| [F4](#f4--six-directories-violate-hard-rule-8) | Six directories have no `README.md` | P2 | **now** | `spec` |
| [F5](#f5--semantic-layer-format-is-undecided-against-odts) | Semantic-layer format undecided against `@odts` | P3 | when [#20](https://github.com/dataengy/ogip/issues/20) starts | `spec` |
| [F6](#f6--issue-19-body-has-drifted-from-its-task-file) | Issue #19 body drifted from its task file | P3 | **now** | not `spec` |
| [F8](#f8--handoff-the-odos-design-still-names-the-umbrella-odps) | ODOS design still names the umbrella `ODPS` | **P1** | when the ODOS spec lands | ODOS lane |

_F7 (ODTS vs the Open Transformation Specification) was evaluated and closed — verdict in
[docs/comparisons/ots-vs-odts.md](../docs/comparisons/ots-vs-odts.md); the alignment work it
produced lives on [#35](https://github.com/dataengy/ogip/issues/35) and
[#36](https://github.com/dataengy/ogip/issues/36)._

## F8 — handoff: the ODOS design still names the umbrella `ODPS`

`docs/superpowers/specs/2026-07-20-odos-orchestration-spec-design.md` (uncommitted at the time
of writing, *"awaiting approval → ADR-0017"*) states the taxonomy with **ODPS** as the umbrella.
The `spec` lane renamed it to **YADPS** in
[ADR-0016](../docs/adr/ADR-0016-odts-authoring-format-spec-sql.md) after finding the acronym held
by Bitol's Open Data Product Standard and the Linux Foundation's Open Data Product Specification
— with Bitol also maintaining ODCS, already used by `spec/contracts/`.

**Timing, not disagreement:** the rename landed after that design was drafted. Left as a handoff
because the file belongs to the ODOS lane; editing another lane's in-flight design would be the
thing this register exists to prevent.

**For the ODOS lane, when that spec lands:**
- umbrella is **YADPS** (Yet Another Data Platform Standard); ODTS and ODOS keep `Open` — checked,
  unclaimed;
- the convention behind it: **a name colliding with an existing standard takes `YA` in place of
  `Open`** — check before minting the next one;
- `ADR-0017` is yours; the `spec` lane took `ADR-0016` and is not claiming further numbers.

**Already done, no action needed:** that design's own naming note asks the `spec` lane to fix
ODTS's expansion (*"Spec"* → *"Standard"*) and the *"not a published standard"* line in
`spec/sql/AGENTS.md`. Both landed in `aee50ca`.

---

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

## F4 — six directories violate hard rule 8

[AGENTS.md](AGENTS.md) hard rule 8: *"Every new directory gets a `README.md`."* Missing in
`spec/sql`, `spec/sql/{staging,core,raw,fs}`, `spec/contracts`. Pre-existing, not introduced
by the `@odts` work.

`spec/sql` now has [AGENTS.md](../spec/sql/AGENTS.md), which covers *authoring rules* but is
not a README and does not satisfy the rule. The layer directories are the more useful gap:
`raw`/`staging`/`core`/`fs` encode the layer-naming law
([ADR-0001](../docs/adr/ADR-0001-edw-layering-no-medallion.md)) and currently explain it
nowhere local.

## F5 — semantic-layer format is undecided against `@odts`

[tasks/spec-semantic-layer.md](tasks/spec-semantic-layer.md) ([#20](https://github.com/dataengy/ogip/issues/20))
plans semantic definitions in **Bruin Semantic Layer** YAML. `@odts` covers `spec/sql` only, so
the two do not collide today — but landing `@odts` while #20 adds a second Bruin-format surface
re-opens the same vendor-marker argument ADR-0016 just settled.

**Decide before #20 starts:** does the semantic layer follow `@odts`, stay Bruin YAML as a
deliberate exception, or become plain YAML with no vendor marker? Cheap now, expensive after
the definitions exist.

## F6 — issue #19 body has drifted from its task file

`just tasks-sync --dry-run` reports a pending body update for
[#19 `sources-backlog`](https://github.com/dataengy/ogip/issues/19). The drift predates the
`@odts` work and belongs to another lane.

**Do not fix by running the full sync** — it would push this lane's drift under your name.
Whoever owns `sources-backlog` should sync it, or use the targeted path (import
`src/scripts/tasks_sync.py` and call `_update` for that slug alone).
