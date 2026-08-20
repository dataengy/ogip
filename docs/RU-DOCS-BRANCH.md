# The `ru-docs` branch — versioned Russian translations

> 🇷🇺 Русская версия: [RU-DOCS-BRANCH.ru.md](RU-DOCS-BRANCH.ru.md)

Long-lived branch (worktree: `../OGIP.worktrees/ru-docs`), never merged into `dev`
([#55](https://github.com/dataengy/ogip/issues/55)). It exists because on `dev` every
`*.ru.md` is **gitignored by design** — translations there are machine-local and would die
with the workstation. This branch is the **bilingual view**: translations are force-added
(`git add -f`) and pushed, and the beginning-of-file mirror-refs (EN doc ↔ RU sibling) exist
**only here** — on `dev` such links would be broken for every clone.

| Artifact | dev | ru-docs |
|---|---|---|
| `*.ru.md` translations | gitignored, untracked | committed (`git add -f`) |
| EN→RU mirror-ref line in sources | absent | present (after the H1) |
| RU→EN mirror-ref line in translations | n/a | present (after the provenance header) |
| `docs/TRANSLATIONS.ru.{yml,md}` manifest | derived, untracked | committed |

## Update loop (run inside this worktree)

```bash
git merge origin/dev                     # bring in fresh sources (see conflict note below)
JF=~/.ai/skills/_scripts/docs/translate-ru/Justfile
just -f "$JF" enumerate --scope all      # missing/stale sources (mtime); manifest sha is authority
# translate the listed sources (/translate-md-docs-to-russian — model step)
just -f "$JF" mirror-refs --repo "$PWD" --sources-file <list> --sha-bump --skip-sha-file <stale>
just -f "$JF" manifest-all               # from the worktree root
git add -f -- '*.ru.md' docs/TRANSLATIONS.ru.yml && git add -A
git commit && git push origin ru-docs    # verify origin/ru-docs..ru-docs first, separately
```

Known traps (all confirmed the hard way): every recipe except `enumerate` needs an ABSOLUTE
`--repo` (just resolves `.` against the Justfile dir); `enumerate --paths` silently takes ONE
path per call; a freshly copied/checked-out `.ru.md` defeats mtime staleness — trust the
manifest's `sha` states instead.

## Merge conflicts with dev

The EN mirror-ref line sits right after each H1, so a dev-side edit near a file's top can
conflict on merge. Resolution is always: keep dev's content **and** keep the branch's
mirror-ref line. A dev-side content change makes the recorded sha stale → the file shows up
in the next enumerate/manifest pass for retranslation.

## What must never happen here

- No merge/PR of `ru-docs` into `dev` (it would carry the tracked translations and the
  EN-side link lines into every clone). Since 2026-08-20 this is enforced
  ([#57](https://github.com/dataengy/ogip/issues/57)): `ru-docs` is **branch-protected**
  (no deletion, no force-push) and **exempt from the repo's squash-only PR-merge rules** —
  it is listed under `never_merge` + `long_lived` in
  `~/.ai/skills/.settings/branch_rules.yml#pr_merge`. It updates itself only via
  `git merge origin/dev` inside this worktree.
- No hand-edits of `*.ru.md` bodies — fix the EN source and retranslate (the provenance
  header says exactly that).
- No commits of `*.local.md` / machine-local sources' translations (their EN originals are
  untracked on dev; the orphaned RU files stay untracked here too).
