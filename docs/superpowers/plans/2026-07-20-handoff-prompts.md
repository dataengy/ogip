# Handoff prompts — session `3ad45e75` (OGIP @ dev)

```
# origin: cd ~/gi/@dataengy/OGIP && claude --resume 3ad45e75-ed02-41d9-a624-c6f1919e81d1 # OGIP sources + skills decomposition
```

Fan-out of the remaining work: 6 prompts for 6 different receivers. Each carries where the work
lives · what is already established (do not re-derive) · the exact next step · the trap this
session already hit.

Written in English per `/handoff-prompts` `settings/defaults.yml#lang.default` — the receiving
repos are authored in English even though this session was conducted in Russian.

**Closed this session, do not redo:** Kickstarter registered FORBIDDEN and pushed (`bc152e0`) ·
`/github-auth-ensure` skill + script + settings + SessionStart hook built and committed
(`d98883c`) · `.ai/SKILLS.md` applicability filter written · agents and plans pushed
(`d6df7be`, `2b4a279`).

---

## 1 → Skills-catalog session — Wave 1

```
Create the three Wave 1 skills from the proposal at
/Users/nk.myg/gi/@dataengy/OGIP/docs/superpowers/plans/2026-07-20-add-data-source-skill-decomposition.md
(section "Wave 1"): describe-source-business-value and design-source-pipeline under
de/ingestion, generate-synthetic-fixtures under a new de/testing area.

Already established — do not re-verify: all 521 catalog skills were audited. These three have
ZERO coverage (grep for 'synthetic data|fixture generat|mock data|faker' returns 0 hits). Do
NOT create an ODCS skill — /generate-odcs-specs in de/contracts/ already covers that
completely. The extraction boundary is set by /find-sources-and-match-tool, which already owns
the parent's Steps 0-2 (research + probe + route); your skills begin AFTER routing.

Next step: run /propose-skill-for-that first and wait for its gate, then /create-skill for
each. Skill files are never hand-written — that is a standing policy. Run
/save-all-deterministic-for-skill-as-scripts <slug> after each, then skill-sync-state.

Trap this session hit: `~/.claude/skills/<slug>/skill.md` can be an independent STALE copy
rather than a hardlink to the catalog — /add-data-source was found running a version 3 days and
6 KB behind, with no symptom. `deploy-skill` only refreshes the `agents` symlink and leaves
claude STALE; `hardlink-skill-files <catalog-dir> <target-dir>` is what actually repairs it. I
hit this twice, including on the skill I created today. Check sync-state after EVERY edit.
```

## 2 → Skills-catalog session — Wave 2 (after Wave 1)

```
Create the five Wave 2 implementer skills from
/Users/nk.myg/gi/@dataengy/OGIP/docs/superpowers/plans/2026-07-20-add-data-source-skill-decomposition.md:
write-ingestion-dlt / -ingestr / -airbyte-oss / -scraping / -complex-api under de/ingestion.

Already established: the cut is not arbitrary — it mirrors the router vocabulary in
~/.ai/skills/.settings/de/ingestion/tool_routing.yml (8 verdicts). Only the five live ones need
skills; spark and gcp are reserved with no registry precedent and none means FORBIDDEN, so do
not create skills for those three.

Next step, and permission NOT to code: the original request was for five separate dlt skills
(native / standalone / Dagster / OpenDBT / Prefect). The document recommends REFUSING that and
building one write-ingestion-dlt with a "where it runs" section delegating by name to the
existing /add-dagster-module, /integrate-sql-tool-with-prefect and /call-dagster-from-prefect.
Read the argument in "The one place the literal ask should be refused" and decide for yourself;
if you think the split is justified, write down why — but do not silently implement either
shape.

Trap: the shared laws (Layer-0, SSoT config, fixture-size/LFS) must STAY in the parent and be
referenced. Copying them into five skills is exactly the guardrail /split-skill-on-subskills
forbids: "do not leave provider-specific logic duplicated in both parent and subskill."
```

## 3 → OGIP session, lane `ingestion` — Metacritic debt + the DoD gate

```
Execute Tasks 1 and 2 from docs/superpowers/plans/2026-07-20-source-dod-registry-and-domain-docs.md
in /Users/nk.myg/gi/@dataengy/OGIP: the ODCS contract
spec/contracts/metacritic/metacritic__game.odcs.yaml plus the staging model
spec/sql/staging/stg_metacritic__game.sql, then the executable gate .ci/steps/source-dod.sh
with its test src/tests/unit/test_source_dod_check.py.

Already established — do not re-derive: the connector ingestion/sources/metacritic.py (95
lines) ALREADY exists and already lands raw/metacritic__game Parquet, commit dc02ddb. Exactly
the contract and the staging model are missing. The full contract YAML and the full model SQL
are given verbatim in the plan — this is transcription, not design. Freshness SLA is 7d, not
RAWG's 1d (a critic aggregate is static). Gates in this repo run ONLY through
.ci/run.sh <step> → .ci/steps/<step>.sh; there is no root .pre-commit-config.yaml, it lives
under config/.

Next step: read the actual shape of the landed Parquet and write the contract against THAT,
not against what `_record()` in the connector promises.

Trap: source-dod.sh is RED by construction until Task 1 is done. That is its purpose, not a
bug — do not "fix" it by weakening the check. And run /verify-gate-actually-covers before
believing a green run: a gate that matches zero files looks exactly like success. This repo has
already shipped one prose "gate" that nothing enforced.
```

## 4 → OGIP session, lane `docs` — registry, glossary, domain docs

```
Execute Tasks 3, 4 and 5 from docs/superpowers/plans/2026-07-20-source-dod-registry-and-domain-docs.md
(/Users/nk.myg/gi/@dataengy/OGIP): the remaining FORBIDDEN registrations, the glossary terms,
and the new docs/domain/ section.

Already established: Kickstarter is DONE — registered, projected and pushed (bc152e0); three
registrations remain (epic_store_product, gamalytic_game, mobygames_credits). The client's
domain axis is production cost x scope x realised revenue, NOT discounting and NOT wishlist
conversion — wishlists and discount curves appear nowhere in the source material, so a section
about them would be invention. Tier vocabulary is Kei / Midi / AA / AAA. The LinkedIn company
page IS readable, no 403 — an earlier assumption that it was blocked was wrong, do not carry it
forward. The source registry lives OUTSIDE this repo at
~/.ai/skills/.settings/de/ingestion/sources/<area>/<key>.yml; spec/sources/*.yaml is a one-way
generated projection and editing it directly is pointless.

Next step: add glossary terms only through /add-terms-to-glossary, never by hand. This is two
commits in two repositories.

Trap: the production-budget dimension has NO permitted source at all — MobyGames (credits
length) and HowLongToBeat (playtime) are both blocked, and Kickstarter is now blocked too.
Write that into docs/domain/ as an explicit coverage gap. The temptation to paper over it with
a plausible sentence is strong and would produce a document that lies about what the platform
can do.
```

## 5 → A human, not a session — two legal blockers

```
Two questions need a person reading in a browser; an agent cannot close them.

(1) MobyGames API terms. https://www.mobygames.com/info/api/ returns 403 to bots, so its terms
have NEVER been read. They are legally distinct from the site's content signals
(Content-Signal: ai-train=no, an express Article 4 / EU 2019/790 reservation, and a separate
ClaudeBot Disallow: /). Open it in a browser and read it: if the API licence permits derived
datasets, OGIP regains the production-budget dimension — the strongest signal in the whole
domain methodology. Ten minutes of reading against an entire model dimension is the best
effort-to-impact ratio in the backlog.

(2) api.steampowered.com robots interpretation. That file serves `User-Agent: * / Disallow: /`,
yet the source steam_applist is registered publishable: true, tier: direct, routing to dlt on
exactly that host. Strict reading: the source is in breach and Steam Charts needs Playwright.
"robots does not govern a documented API" reading: it is fine and Steam Charts collapses to
plain dlt. This is a licence-interpretation judgement, not a technical check, so it belongs to
a human. Until it is answered, no new work should be built against that host; it is recorded as
FIXME F9.
```

## 6 → Skills-repo maintainer — reconcile the baseline branch

```
The ~/.ai/skills repository is on branch chore/track-catalog-baseline with several hundred
modified and untracked files that predate this session, and three of my commits landed on that
branch: 29112cc (kickstarter_project registry entry + AREA_BY_PREFIX mapping) and d98883c
(github-auth-ensure skill + script + settings + session-state hook + add-data-source edits).

Already established: my commits are scoped — each used `git commit -o <explicit paths>` and
swept in nothing else. The surrounding dirt is not mine and I deliberately did not touch it.
Note that _scripts/ and _settings/ were largely UNTRACKED in this repo, so my commits are the
first to track several of those files, including
_scripts/session/session-state-hook.sh and _scripts/git/github-cli/Justfile — which contain
other people's work in the same files.

Next step, and permission not to code: decide whether chore/track-catalog-baseline is the
intended landing branch for functional work like mine, or whether these two commits should be
cherry-picked onto a normal branch and the baseline branch left to do only its baseline job. I
could not tell from the repo which is intended. Read the branch's history first; do not start
by rewriting anything.

Trap: `~/.ai/skills/.settings` is a SYMLINK to `_settings`. `git add .settings/...` fails with
"beyond a symbolic link" — you must use the real `_settings/...` path. I lost a commit attempt
to this.
```

---

## Not in the fan-out

- **Locks:** `obj--agents-skills` is STALE but held by this session; release or refresh it.
  `obj--ingestion` was claimed and released cleanly.
- **Unverified:** how many other catalog skills carry the same stale-claude-copy drift. Two
  found, sample of two — nobody has swept the other ~519.
- **Security observation, not an incident:** the global git credential helper is `store`, which
  keeps tokens in plaintext at `~/.git-credentials` (mode 600). `osxkeychain` would be the
  hardening step. Not migrated — that would change auth for every repo on the machine.
