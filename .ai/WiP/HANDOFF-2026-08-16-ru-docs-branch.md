# HANDOFF — ru-docs branch: state after the 2026-08-16 session (#55)

Pre-compaction snapshot (/compact-safely step 3). Everything below is verifiable on disk/origin.

## Open tasks (with keys)

- **[#55](https://github.com/dataengy/ogip/issues/55)** — 17 translations remain on the
  `ru-docs` branch: 14 missing + 3 sha-stale (translator fleet cut by the session limit,
  resets 07:00 Asia/Tbilisi). Authoritative list: `just -f
  ~/.ai/skills/_scripts/docs/translate-ru/Justfile enumerate --scope all` inside
  `OGIP.worktrees/ru-docs` (missing) + `docs/TRANSLATIONS.ru.yml` sha-states (stale).
  Resume loop: `docs/RU-DOCS-BRANCH.md`. Session task #9 tracks this.
- **[#52](https://github.com/dataengy/ogip/issues/52)** — human-only steps still open:
  `bw unlock` + `just secrets-push` (escrow real values); optional GPG key +
  `just secrets-setup-git-secret`.
- Deferred session nudges: changelog gaps (8 days), `.tmp` review, Todoist guard (now 0 overdue).

## Done (commit SHAs)

- `ru-docs` branch pushed: **d02fa7f** — 140 EN sources with BOF RU-links, 129 committed
  `*.ru.md` (81 translated + 47 sha-bumped), manifest, `docs/RU-DOCS-BRANCH.md`.
- dev: **5c96c4b** CHANGELOG (ru-docs announce) · #52 secrets landed earlier as
  3439cec/85c91bf/054227d · lane/dagster lockfile 755cd12.
- `~/.ai` (all pushed): 277e683 skill catalog · a712244 `mirror-refs.py` · 5b85cb3 skill-doc
  step 2.5 + traps.
- Commit-binding audit: OGIP dev/lanes fully bound; 2 stray `~/.ai` commits bound
  by-reference to hnkovr/.ai#4.

## Unresolved (and why)

- 17 translations — session limit killed 5 of 12 subagents mid-fleet; writes are atomic, so
  present files are complete.
- Pre-existing broken md-refs inside the translate skill's SKILL.md (not introduced here).

## Decisions accepted (do not re-litigate)

- `ru-docs` is long-lived and **never merges into dev**; mirror-refs (both directions) exist
  ONLY on that branch; BOF placement (EN: after H1; RU: after provenance header).
- Deterministic sha-bump — never retranslation — when the only source change is the
  mirror-ref insertion.
- `*.local.md` / machine-local sources' translations stay untracked even on ru-docs.
- Shared-branch binding fixes are by-reference (comments), never history rewrites.
