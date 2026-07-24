# `.ai/SKILLS.md` — which agent skills apply to OGIP

The shared catalog (`~/.ai/skills/_catalog/`, **521 skills**) is built mostly for a *corporate
GitLab + Jira + ClickHouse* platform. OGIP is **public OSS on GitHub with DuckDB**. Roughly
**193 of those 521 skills target infrastructure this project does not have** — so "the catalog has
a skill for that" is not evidence that the skill applies here.

This file is the filter. It exists because an agent reaching for `/merge-mr` or `/add-jira-task` in
this repo does not fail loudly — it produces confident, plausible, wrong work.

**Evidence rule:** a skill is listed under *In use* only with a file that references it. Everything
else is a recommendation, and labelled as one.

---

## 1. In use — referenced by this repo

| Skill | Where OGIP references it | What it does here |
|---|---|---|
| `/agent-session-lock` | [`STATUS.md`](STATUS.md), [`tasks/session-coordination.md`](tasks/session-coordination.md), [`src/scripts/lane.sh`](../src/scripts/lane.sh) | **Mandatory before any write.** 4+ sessions commit to `dev` at once; `lane.sh` wraps this primitive. |
| `/add-data-source` | [`.claude/agents/ogip-ingestion-engineer.md`](../.claude/agents/ogip-ingestion-engineer.md) | The ingestion spine: probe → tier → legality → connector + contract + staging + test → ship. |
| `/find-sources-and-match-tool` | same agent file, `.claude/settings.local.json` | Its research half — registry claims, live probe, deterministic tool routing. |
| `/add-terms-to-glossary`, `/update-terms-glossaries` | [`AI-glossary.en.md`](AI-glossary.en.md), [`AI-glossary.ru.md`](AI-glossary.ru.md) | The **only** sanctioned way to edit the glossaries. Never hand-edit them. |
| `/smart-commit` | [`CLAUDE.md`](CLAUDE.md) | Commit conventions when `ship.sh` does not fit. |
| `/add-secret` | [`src/scripts/ask-secret-gui.sh`](../src/scripts/ask-secret-gui.sh) | Secret-slot intake. Never invent a credential; an empty slot is a question for the user. |
| `/check-secrets` | [`tasks/vps-deploy-tooling.md`](tasks/vps-deploy-tooling.md) | Secrets completeness before a deploy. |
| `/github-auth-ensure` | [`.claude/settings.json`](../.claude/settings.json) SessionStart hook | Will `git push` authenticate as the account that **owns** `dataengy/ogip`? A push here failed `denied to hnkovr` while the correct token was already on disk — a URL-scoped credential helper was shadowing it. The hook warns only on mismatch. |

## 2. Applicable to the stack — recommended, not yet wired

Matched against OGIP's actual engines (Prefect · dbt/SQLMesh/Bruin · DuckDB · Dagster · GitHub
Actions). These are the ones worth reaching for; none is referenced in the repo yet.

| Skill | Use it when |
|---|---|
| **`/generate-odcs-specs`** | Authoring or updating any `spec/contracts/<system>/<system>__<entity>.odcs.yaml`. **This is the ODCS authority** — `/add-data-source` Step 4 item 2 should call it rather than restate contract authoring. |
| **`/generate-agnostic-bruin-sql-specs`** | Writing anything in `spec/sql/` — the `@bruin`→`@odts` portable-SQL format steward. |
| **`/spec-compile-engines`** | The one-spec → N-engine compiler (dbt · SQLMesh · Bruin · plain SQL). Directly matches OGIP's transform architecture. |
| **`/integrate-sql-tool-with-prefect`** | Adding a per-engine Prefect flow. Matches the "one flow per SQL engine" decision already recorded in project memory. |
| **`/call-dagster-from-prefect`** | The Dagster-inside-Prefect seam — `.github/workflows/dagster-e2e.yml` already exercises this shape. |
| **`/add-dagster-module`**, `/add-dagster-odp-module`, `/integrate-dagster-with-dbt` | Work inside `experimental/orchestration/`. |
| **`/verify-gate-actually-covers`** | **Every time a CI gate, prek hook, or regression test is added.** A gate matching zero files looks exactly like a passing gate — and this repo has already shipped one prose "gate" that nothing enforced. |
| **`/e2e-ship`** | Ship-on-green: run e2e, then commit + push + notify. |
| **`/handoff-prompts`** | Fanning out leftover work to other sessions (used by [`docs/superpowers/plans/2026-07-20-handoff-prompts.md`](../docs/superpowers/plans/2026-07-20-handoff-prompts.md)). |
| **`/sync-with-parallel-session`** | Before a merge/restart that another live session may own. |
| **`/session-artifacts-to-tmp`** | Capturing this session's ad-hoc scripts into `.tmp/` per the project's batch-work convention. |
| **`/upsert-doc-about-runbook`**, `/upsert-doc-about-roadmap`, `/validate-docs` | `docs/runbooks/`, `docs/ROADMAP.md`, doc hygiene. |
| **`/ensure-git-repo`**, `/update-gitignore`, `/remove-from-git-index` | Repo hygiene. |
| **`/use-log-alias`** | The `log`-not-`logger` convention, enforced project-wide. |

## 3. Do NOT reach for these here

Not "lower priority" — **wrong infrastructure**. Each would produce work against a system OGIP
does not use.

| Family | Count | Why it does not apply to OGIP |
|---|---|---|
| Jira / Tempo / PNF / Todoist / Linear trackers | **81** | OGIP tracks work in **GitHub Issues** (`just tasks-sync`, `Refs: #<n>` enforced by `.ci/steps/commit-binding.sh`). Zero Jira references exist in this repo. |
| GitLab `glab` / MR review / merge workflows | **36** | OGIP is **GitHub**; `dev → main` goes through a GitHub PR with `.github/workflows/ci.yml`. There are no MRs. |
| `host-ops` — SSH fleet, cron hosts, Zabbix, tunnels | **50** | OGIP has no managed host fleet. Deployment is local compose + a single VPS task. |
| ClickHouse + dbt-submodule operations | **26** | The warehouse is **DuckDB**. dbt exists only as one *generated* engine under `experimental/`, never as a submodule. |

**The trap this table prevents:** these skills are well-written and will execute happily. The
failure is silent — a correctly-formed Jira task for a project with no Jira, a `glab` call against
a repo with no GitLab remote. Check this table before reaching, not after.

## 4. Gaps — proposed, not yet created

Four capabilities have **zero** coverage across all 521 skills: source business-value description,
source→landing→staging pipeline design, **synthetic fixture generation** (0 hits catalog-wide), and
per-engine connector authoring.

Full decomposition, with the reuse audit and a three-wave build order:
[`docs/superpowers/plans/2026-07-20-add-data-source-skill-decomposition.md`](../docs/superpowers/plans/2026-07-20-add-data-source-skill-decomposition.md).

Nothing there is created yet. Creation is gated and runs through `/propose-skill-for-that` →
`/create-skill` → `/save-all-deterministic-for-skill-as-scripts` — **skill files are never written
by hand.**

## 5. The skill that should maintain this file — generalize, don't create

This file was assembled by hand. It should not be, and **the fix is not a new skill.**

`/analyse-pdp-skill-usage` already does the counting half: it scans a project root for known slugs
across plans, FIXMEs, TODOs and sessions, and emits `skill-usage.yml` + `skill-task-map.md` +
`used-skills.list`. Two changes make it produce §1–§3 of this document:

1. **Generalize it off PDP.** Its project root is already externalized to `settings/defaults.yml`;
   the rename `analyse-pdp-skill-usage` → `analyse-project-skill-usage` is what
   `/refactor-repo-root-to-project-param` exists to do. Nearly mechanical.
2. **Add the applicability filter it lacks.** Usage counting answers *"which skills does this
   project mention"*. It does not answer *"which skills would silently produce wrong work here"* —
   §3 above, the highest-value part. That needs a per-project capability declaration (tracker =
   github|jira · vcs-host = github|gitlab · warehouse = duckdb|clickhouse · host fleet = yes|no)
   checked against each skill's area.

Creating a fresh `index-project-skills` skill instead would leave two overlapping scanners to drift
apart — the exact duplication `/split-skill-on-subskills` guards against.

## 6. Keeping this file honest

- A skill moves from §2 to §1 only when a real file references it. Do not promote on intent.
- **Verify before recommending.** Catalog skills are edited outside this repo; confirm a slug still
  exists with `just -f ~/.ai/skills/_scripts/skills/management/Justfile skill-locate <slug>`.
- **Skill copies drift silently.** `~/.claude/skills/<slug>/skill.md` may be an independent stale
  copy rather than a hardlink to the catalog — `/add-data-source` was found running a version 3 days
  and 6 KB behind, with no symptom. After any catalog edit run `skill-sync-state <slug>` and fix
  `STALE`; `hardlink-skill-files <catalog-dir> <target-dir>` is what actually repairs it.
- The §3 counts are a snapshot (2026-07-20) of a catalog that grows. The *reasoning* is stable; the
  numbers are not.
