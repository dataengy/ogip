# Stale branches register (owner directive 2026-07-30: mark, never delete)

Branches whose work is fully contained in `dev` (or superseded). They are **kept as
pointers** — do not develop on them, do not rebase them, do not delete them. Verify
containment before trusting: `git rev-list --left-right --count origin/dev...<branch>`
(ahead 0 = contained).

| Branch | Tip | State | Landed via |
|---|---|---|---|
| `lane/reroot-dbt-bruin-primary` | `2d3b9da` | stale — merged | PR #46 (re-root T1–T9, ADR-0020) |
| `lane/neighbour-salvage` | `b32c3e2` | stale — merged | PR #45 (ODTS fixture parity + ru-gitignore) |
| `lane/core-pipeline` | `90383ec` | stale — contained | merged into dev pre-finalization |
| `lane/transform-dq-expansion` | `452ad8c` | stale — contained | merged into dev pre-finalization |
| `lane/airbyte` | `5d67276` | stale — contained (== old dev tip) | evaluation lane, runtime NO-GO (#41) |
| `lane/evidence` · `lane/obs` · `lane/s3` · `lane/vps` | `1b9071d` | stale — empty placeholders (138+ behind), no unique work | never developed |
| `lane/dagster` | `645d190` | stale — merged 2026-07-30 | PR #34 (flattened defs, warehouse split, dbt-native DQ) |
| `lane/odos-compiler` | `6669142` | stale — merged 2026-07-30 (adapters/equivalence stay open on #37) | PR #49 |

History note: on 2026-07-30 (finalization step 18) these pointers were briefly deleted after
containment proof, then restored at their exact tips the same day when the owner set the
mark-don't-delete policy. No commits were ever lost. Frozen *features* live in
[finalization-tbd.md](finalization-tbd.md) — loud stubs + issues, never silent removal.
