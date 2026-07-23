# Source Definition-of-Done, registry truth, and the business-domain docs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the Metacritic source debt, make the Definition of Done an executable gate instead of prose, record the 2026-07-20 source-research findings as registry truth, and give OGIP the business-domain vocabulary and documentation it currently has none of.

**Architecture:** Six independent tasks, ordered so each one's verification is meaningful. Task 1 repays the debt; Task 2 installs the check that stops it recurring (it cannot pass before Task 1 lands, which is the point); Tasks 3–6 are documentation and registry truth, each independently shippable.

**Tech Stack:** ODCS v3 contracts (`spec/contracts/`) · `@bruin` portable SQL (`spec/sql/`) · the out-of-repo ingestion registry (`~/.ai/skills/.settings/de/ingestion/`) · bash + `prek` for the gate · `/update-terms-glossaries` for glossaries · `gh` for issues.

## Global Constraints

- **Lane discipline.** Claim the lock before writing: `bash src/scripts/lane.sh acquire <lane> "<reason>"`. Lanes used here: `ingestion` (Tasks 1–2), `spec` (Task 1 SQL), `docs` (Tasks 4–5). Four-plus agent sessions share this branch.
- **Never `git add -A`.** Parallel sessions leave staged files in the shared index. Use `git commit -o <paths>`.
- **Every commit carries `Refs: #<n>` or `Closes: #<n>`** — enforced by `.ci/steps/commit-binding.sh`.
- **Never force-push** `dev` or `main`.
- **This repo is PUBLIC.** Run `bash src/scripts/public-hygiene.sh` before shipping any prose.
- **`spec/sources/*.yaml` is GENERATED.** Never edit it. Edit the registry SSoT at `~/.ai/skills/.settings/de/ingestion/sources/games/<key>.yml`, then re-emit.
- **`spec/sql/` uses the `@bruin` header today.** ADR-0016 migrates it to `@odts`, but that lands with [#35](https://github.com/dataengy/ogip/issues/35). Match the neighbouring `stg_games.sql` — do not hand-migrate one file ahead of the fleet.
- **Layer-0 law:** raw is `<system>__<entity>`, 1:1 AS-IS, and the only added columns are `_ingested_at` and `etl_batch_id`. Casting and renaming belong in staging.
- **Registry work happens in a different repository** (`~/.ai/skills/`) and needs its own commit — it is not part of any OGIP commit.

---

### Task 1: Metacritic ODCS contract + staging model

Commit `dc02ddb` shipped `ingestion/sources/metacritic.py` and landed `raw/metacritic__game` Parquet, but no contract and no staging model. The raw table currently feeds nothing.

**Files:**
- Create: `spec/contracts/metacritic/metacritic__game.odcs.yaml`
- Create: `spec/sql/staging/stg_metacritic__game.sql`
- Reference (do not modify): `spec/contracts/rawg/rawg__games.odcs.yaml`, `spec/sql/staging/stg_games.sql`, `ingestion/sources/metacritic.py:74-92`

**Interfaces:**
- Consumes: the record shape emitted by `MetacriticGame._record()` — `slug`, `content_hash`, `source_url`, `name`, `released`, `genre`, `publisher`, `metascore`, `review_count`; plus `_ingested_at` and `etl_batch_id` added by `BaseSource.run`.
- Produces: `staging.stg_metacritic__game` with the key column `game_slug`, consumable by any later `core.*` model.

- [ ] **Step 1: Confirm the raw shape before writing the contract**

Do not transcribe from the source code alone — verify what actually landed.

```bash
make run
python3 -c "
import duckdb, glob
f = sorted(glob.glob('.run/data/raw/metacritic__game/**/*.parquet', recursive=True))
print('files:', f)
con = duckdb.connect()
print(con.execute(f\"describe select * from read_parquet('{f[0]}')\").fetchdf())
print(con.execute(f\"select * from read_parquet('{f[0]}')\").fetchdf())
"
```

Expected: one row (Hades, metascore 93, review_count 61, publisher "Supergiant Games"), and exactly the 9 record columns plus `_ingested_at` and `etl_batch_id`. If the column set differs from the list in **Interfaces** above, the contract follows *reality*, not this plan — and say so in the commit body.

- [ ] **Step 2: Write the ODCS contract**

Create `spec/contracts/metacritic/metacritic__game.odcs.yaml`:

```yaml
# Open Data Contract Standard (ODCS) v3 — Metacritic game pages, Layer-0 raw dataset.
apiVersion: v3.0.0
kind: DataContract
id: metacritic-game-raw
name: metacritic__game
version: 0.1.0
status: draft
domain: games
tenant: ogip
description:
  purpose: Immutable 1:1 AS-IS capture of the schema.org VideoGame JSON-LD on Metacritic game pages (Layer 0).
  usage: Source for staging.stg_metacritic__game — the quality dimension (critic aggregate).
  limitations: >
    NOT PUBLISHABLE. robots.txt permits /game/ (verified 2026-07-18) but the Metacritic/Fandom
    Terms of Use have not been reviewed for redistribution of critic aggregates; see
    spec/sources/games/metacritic_game.yaml. Demo mode parses a synthetic fixture; live mode is
    gated behind OGIP_METACRITIC_LIVE=1.

servers:
  - server: local-fs
    type: local
    format: parquet
    path: .run/data/raw/metacritic__game/

schema:
  - name: metacritic__game
    logicalType: object
    physicalType: parquet
    properties:
      - name: slug
        logicalType: string
        required: true
        unique: true
        description: Page slug from the URL — the natural key.
      - name: content_hash
        logicalType: string
        required: true
        description: SHA-256 of the raw JSON-LD block; the landing-upsert change signal.
      - name: source_url
        logicalType: string
        required: true
        description: The page this record was extracted from.
      - name: name
        logicalType: string
        required: true
      - name: released
        logicalType: date
        description: schema.org datePublished.
      - name: genre
        logicalType: string
      - name: publisher
        logicalType: string
        description: First entry of the JSON-LD publisher array.
      - name: metascore
        logicalType: integer
        description: Metascore (0-100) from aggregateRating.ratingValue.
      - name: review_count
        logicalType: integer
        description: aggregateRating.reviewCount.
      - name: _ingested_at
        logicalType: string
        description: Layer-0 ingestion timestamp (ISO-8601 UTC).
      - name: etl_batch_id
        logicalType: string
        description: Layer-0 batch id.

quality:
  - rule: unique
    property: slug
    severity: error
  - rule: not_null
    property: name
    severity: error
  - rule: not_null
    property: content_hash
    severity: error

slaProperties:
  - property: freshness
    value: 7
    unit: d
    element: metacritic__game._ingested_at

team:
  - username: data-eng@ogip
    role: owner
```

Note the freshness SLA is 7d, not RAWG's 1d: a critic aggregate for a released title is near-static, and a 1d SLA would alert on a non-problem.

- [ ] **Step 3: Write the staging model**

Create `spec/sql/staging/stg_metacritic__game.sql`. Match `stg_games.sql` exactly in header style and the leading-comma SQL layout:

```sql
/* @bruin
name: staging.stg_metacritic__game
type: duckdb.sql
materialization:
  type: table
owner: data-eng@ogip
tags: [staging, metacritic, daily]
depends:
  - raw.metacritic__game
columns:
  - name: game_slug
    type: varchar
    checks: [{name: not_null}, {name: unique}]
  - name: name
    type: varchar
    checks: [{name: not_null}]
  - name: metascore
    type: integer
@bruin */
select
    slug as game_slug
    , name
    , try_cast(released as date) as released_date
    , genre
    , publisher
    , cast(metascore as integer) as metascore
    , cast(review_count as integer) as review_count
    , content_hash
    , source_url
    , cast(_ingested_at as timestamp) as ingested_at
    , etl_batch_id
from raw.metacritic__game
```

- [ ] **Step 4: Verify the model compiles and runs**

```bash
make check
make run
```

Expected: `make check` green (ruff, pyright strict, pytest). `make run` builds `staging.stg_metacritic__game` with one row and no check failures. If the runner does not pick the model up automatically, find how `stg_games` is registered and register this one the same way — do not special-case it.

- [ ] **Step 5: Commit**

```bash
bash src/scripts/public-hygiene.sh
git add spec/contracts/metacritic/metacritic__game.odcs.yaml spec/sql/staging/stg_metacritic__game.sql
git commit -o spec/contracts/metacritic/metacritic__game.odcs.yaml spec/sql/staging/stg_metacritic__game.sql -F - <<'EOF'
feat(spec): ODCS contract + staging model for metacritic__game

Repays the debt from dc02ddb: the ScraperSource slice landed raw Parquet
with neither a contract nor a consumer, so the raw table fed nothing and
no gate noticed.

Freshness SLA is 7d (not RAWG's 1d) — a critic aggregate for a released
title is near-static.

Closes: #18
EOF
```

---

### Task 2: Make the Definition of Done an executable gate

The rule "contract + test ship with the connector" existed in `/add-data-source` as prose, one section above the code that ignored it. Prose is not a gate.

**Files:**
- Create: `.ci/steps/source-dod.sh`
- Modify: `Justfile` (the `check:` and `ci:` recipes), `config/.pre-commit-config.yaml`, `.github/workflows/ci.yml`
- Test: `src/tests/unit/test_source_dod_check.py`

The gate is a **CI step**, not a loose script: this repo routes every gate through `.ci/run.sh <step>` with the step body in `.ci/steps/<step>.sh`, so GitHub Actions and local runs execute the identical code. `src/scripts/` is for operator tooling; a gate that CI must run belongs in `.ci/steps/`.

**Interfaces:**
- Consumes: `config/config.yml` `sources:` block (the enabled-source list), `spec/contracts/`, `spec/sql/staging/`. Root override for tests: `SOURCE_DOD_ROOT`.
- Produces: exit 0 when every enabled source has a contract and a staging model; exit 1 with a per-source report naming the missing artifact.

- [ ] **Step 1: Write the failing test**

Create `src/tests/unit/test_source_dod_check.py`:

```python
"""The source Definition-of-Done gate: every enabled source needs a contract + staging model."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / ".ci" / "steps" / "source-dod.sh"


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "SOURCE_DOD_ROOT": str(root)},
        capture_output=True,
        text=True,
        check=False,
    )


def test_passes_on_the_real_repo() -> None:
    """Every source enabled in config.yml has its contract and staging model."""
    result = _run(REPO)
    assert result.returncode == 0, result.stdout + result.stderr


def test_names_the_missing_artifact(tmp_path: Path) -> None:
    """A source with no contract fails loudly and names what is missing."""
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "config.yml").write_text(
        "sources:\n  ghost:\n    enabled: true\n    entities: [thing]\n", encoding="utf-8"
    )
    (tmp_path / "spec" / "contracts").mkdir(parents=True)
    (tmp_path / "spec" / "sql" / "staging").mkdir(parents=True)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ghost__thing" in result.stdout
    assert "contract" in result.stdout.lower()


def test_disabled_sources_are_not_required(tmp_path: Path) -> None:
    """`enabled: false` is the documented way to park an aspirational source."""
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "config.yml").write_text(
        "sources:\n  ghost:\n    enabled: false\n    entities: [thing]\n", encoding="utf-8"
    )
    (tmp_path / "spec" / "contracts").mkdir(parents=True)
    (tmp_path / "spec" / "sql" / "staging").mkdir(parents=True)

    assert _run(tmp_path).returncode == 0
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest src/tests/unit/test_source_dod_check.py -v
```

Expected: FAIL — the script does not exist yet (`bash: .../source-dod-check.sh: No such file`).

- [ ] **Step 3: Write the script**

Create `.ci/steps/source-dod.sh`. Source `_common.sh` like every other step — it sets `set -euo pipefail`, resolves `REPO_ROOT`, `cd`s there, and provides `log`:

```bash
#!/usr/bin/env bash
# Source Definition-of-Done gate — every ENABLED source in config/config.yml must have an
# ODCS contract and a staging model. Exists because the rule lived in prose and was skipped:
# metacritic__game landed as raw Parquet with neither, and nothing failed.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

ROOT="${SOURCE_DOD_ROOT:-$REPO_ROOT}"
CONFIG="$ROOT/config/config.yml"
CONTRACTS="$ROOT/spec/contracts"
STAGING="$ROOT/spec/sql/staging"

die() { echo "[ci] ERROR: $*" >&2; exit 2; }

[[ -f "$CONFIG" ]] || die "no config at $CONFIG"

# Emit "<system> <entity>" per enabled source. Python, not awk: the config is YAML, and a
# regex over nested YAML is how silent misparses get shipped.
mapfile -t PAIRS < <(python3 - "$CONFIG" <<'PY'
import sys, yaml
cfg = yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}
for system, spec in (cfg.get("sources") or {}).items():
    if not (spec or {}).get("enabled"):
        continue
    for entity in (spec or {}).get("entities") or []:
        print(f"{system} {entity}")
PY
)

failed=0
for pair in "${PAIRS[@]}"; do
    read -r system entity <<<"$pair"
    table="${system}__${entity}"

    if [[ ! -f "$CONTRACTS/$system/$table.odcs.yaml" ]]; then
        log "MISSING contract  $table  → expected $CONTRACTS/$system/$table.odcs.yaml"
        failed=1
    fi
    if [[ ! -f "$STAGING/stg_$table.sql" && ! -f "$STAGING/stg_$system.sql" ]]; then
        log "MISSING staging   $table  → expected $STAGING/stg_$table.sql"
        failed=1
    fi
done

if [[ "$failed" -eq 0 ]]; then
    log "source-dod: OK — ${#PAIRS[@]} enabled source(s), all contracted and consumed"
    exit 0
fi

log ""
log "A source that lands raw Parquet with no contract and no consumer is a demo, not a source."
log "See /add-data-source Step 4 — Definition of Done."
exit 1
```

Note the staging check accepts `stg_<system>.sql` as well: `rawg__games` is consumed by `stg_games.sql`, and the gate must describe the repo that exists rather than force a rename.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
chmod +x .ci/steps/source-dod.sh
uv run pytest src/tests/unit/test_source_dod_check.py -v
bash .ci/run.sh source-dod
```

Expected: all three tests PASS. The direct run prints `source-dod: OK` — but **only if Task 1 has landed**. If it reports `MISSING contract metacritic__game`, the gate is working and Task 1 is incomplete. Note `steam` is enabled in `config.yml` with entities `[games, reviews]` and has no connector at all: if the gate flags it, that is a true finding — either the config entry is aspirational and should be `enabled: false`, or the source is genuinely owed. Resolve it explicitly; do not weaken the gate to hide it.

- [ ] **Step 5: Wire the gate into `check`, `ci`, the prek hooks and GitHub Actions**

`Justfile` is a **contested file** — `ship.sh` refuses it unless you hold its object lock. Claim it:

```bash
bash ~/.ai/skills/_scripts/session/agent-session-lock.sh acquire --repo . \
  --object Justfile --reason "wire source-dod gate into check"
```

Four edits. Read each file immediately before editing — they move under you.

1. `Justfile` — add a recipe and put it in the `check` chain:

```just
check: lint typecheck test source-dod

# Every enabled source has an ODCS contract and a staging model
source-dod:
    bash .ci/run.sh source-dod
```

2. `Justfile` — add the step to the `ci:` recipe so local CI parity stays exact:

```just
    bash .ci/run.sh source-dod
```

3. `config/.pre-commit-config.yaml` — add to the existing `repo: local` block, matching the `ty` / `pytest-smoke` entries already there:

```yaml
      - id: source-dod
        name: source Definition-of-Done (contract + staging per enabled source)
        entry: bash .ci/run.sh source-dod
        language: system
        pass_filenames: false
        files: '^(config/config\.yml|spec/(contracts|sql/staging)/)'
```

4. `.github/workflows/ci.yml` — add `source-dod` alongside the other `.ci/run.sh` steps. If the workflow enumerates steps in a matrix, add it to the matrix rather than as a bespoke job.

- [ ] **Step 6: Commit**

```bash
bash src/scripts/public-hygiene.sh
make check
PATHS=".ci/steps/source-dod.sh src/tests/unit/test_source_dod_check.py Justfile config/.pre-commit-config.yaml .github/workflows/ci.yml"
git add $PATHS
git commit -o $PATHS -F - <<'EOF'
ci(sources): executable Definition-of-Done gate for data sources

Every enabled source in config.yml must have an ODCS contract and a staging
model. The rule already existed in /add-data-source as prose and was skipped
anyway — dc02ddb shipped metacritic__game with neither and no gate noticed.

Refs: #18
EOF
```

---

### Task 3: Record the 2026-07-20 source-research findings as registry truth

Research on 2026-07-20 produced four FORBIDDEN verdicts, one unresolved robots conflict, and evidence that one rung of the ADR-0014 escalation ladder has no legitimate use case. None of it is recorded, so the next agent will re-derive it.

**Files (registry — the `~/.ai/skills/` repository, separate commit):**
- Create: `~/.ai/skills/.settings/de/ingestion/sources/games/{epic_store_product,kickstarter_project,gamalytic_game,mobygames_credits}.yml`

**Files (OGIP):**
- Modify: `.ai/tasks/sources-backlog.md` (rows 8 and 12), `.ai/FIXME.md` (new entry), `docs/adr/ADR-0014-resilient-scraping-concurrency.md`
- Generated, do not hand-edit: `spec/sources/games/*.yaml`

- [ ] **Step 1: Register the four forbidden sources**

Model each on the existing `hltb_games.yml` — the established shape for a prohibition entry. Each needs `do_not_fetch: true`, a `license:` starting `FORBIDDEN-`, a `license_note:` quoting the evidence **verbatim with its date**, and a `provenance:` block. The verdicts, all verified 2026-07-20:

| key | url | evidence to quote |
|---|---|---|
| `epic_store_product` | `https://store.epicgames.com/` | `robots.txt` itself returns **HTTP 403** — a Cloudflare challenge page (25,353 B, `Enable JavaScript and cookies to continue`). The permission document is unreadable, so no fetch grant can be established. |
| `kickstarter_project` | `https://www.kickstarter.com/` | `robots.txt` returns **HTTP 403** Cloudflare interstitial (`<title>Just a moment...</title>`). Confirms the 2026-07-18 backlog finding. |
| `gamalytic_game` | `https://gamalytic.com/` | `robots.txt` returns a `Vercel Security Checkpoint` challenge page. |
| `mobygames_credits` | `https://www.mobygames.com/` | robots.txt carries `Content-Signal: search=yes,ai-train=no,use=reference` with an express Article 4 / EU Directive 2019/790 reservation, **and** a separate `User-agent: ClaudeBot` / `Disallow: /`. `ai-train=no` targets exactly what OGIP ships. |

For `mobygames_credits`, record the honest limit of the evidence: their `/info/api/` page returned 403 to automated fetch, so the **API's** terms — legally distinct from the site's content signals — were not read. The entry blocks the *scrape*; a human reading the API terms in a browser could still unblock the API. Do not present the site verdict as an API verdict.

- [ ] **Step 2: Validate and re-emit the projection**

```bash
JF=~/.ai/skills/_scripts/de/ingestion/Justfile
just -f "$JF" split-check
just -f "$JF" probe-all          # FORBIDDEN entries must NOT be fetched — verify that in the output
just -f "$JF" route-all          # each new entry must route to `none` [forbidden]
just -f "$JF" spec-emit /Users/nk.myg/gi/@dataengy/OGIP games
just sources-drift
```

Expected: `route-all` shows the four new keys as `none [forbidden]`; `probe-all` opens no connection to them; `sources-drift` exits 0.

- [ ] **Step 3: Rewrite the two stale backlog rows**

In `.ai/tasks/sources-backlog.md`, row 8 (MobyGames) currently reads as an open candidate and row 12 (Kickstarter) as a soft warning. Both are now blocked. Rewrite them in the established style of the HLTB and SteamDB rows — strikethrough the source name, `⛔ FORBIDDEN` with a link to the registered descriptor, and state what dimension is left uncovered. For MobyGames that is **production budget / team size**, which loses its main candidate.

Add a line under "Grooming rules" recording what the sweep found: the permitted candidates it turned up (Nintendo eShop, Xbox Store, GOG) are all server-rendered or clean REST — useful, but none of them justify a new fetch tier.

- [ ] **Step 4: Record the unresolved Steam robots conflict in the FIXME register**

Add entry **F9** to `.ai/FIXME.md`, in both the index table and the body. The failure, stated as a failure:

`steam_applist` is registered `tier: direct`, `publishable: true`, routes to `dlt`, and sits on `api.steampowered.com`, whose `robots.txt` reads `User-Agent: *` / `Disallow: /` (re-verified 2026-07-20). Its own descriptor acknowledges this and defers it. The same ruling also decides whether Steam's `/charts/` pages need Playwright (strict reading) or collapse to a plain REST call against `ISteamChartsService` (documented-API reading). Severity **P1**, wrong **now**, owner lane `ingestion`. State plainly that this needs a *human* verdict — it is a licence-interpretation question, not a technical one — and that until it is answered, nothing new should be built against `api.steampowered.com`.

- [ ] **Step 5: Mark the unevidenced rung in ADR-0014**

ADR-0014 §6 states the escalation ladder `httpx → curl_cffi → playwright` as though all three were live. After the sweep: every registered scraping source is served by plain `httpx` with `render: false`; the only evidenced case for **Playwright** is Steam's `/charts/` SPA (blocked on F9); and **no source in this domain justifies `curl_cffi`** — every candidate that would have needed TLS-fingerprint parity turned out to be hostile-and-forbidden rather than hard-and-permitted.

Add a short dated note to that effect. Do not delete the rung — record it as speculative, with the date and the sweep that found nothing. ADR-0014 is `Status: Proposed`; a note is appropriate, a rewrite is not.

- [ ] **Step 6: Commit — two commits, two repositories**

```bash
# 1) registry repo
git -C ~/.ai/skills add .settings/de/ingestion/sources/games/
git -C ~/.ai/skills commit -m "feat(ingestion): register four FORBIDDEN games sources (2026-07-20 sweep)"

# 2) OGIP
bash src/scripts/public-hygiene.sh
git add .ai/tasks/sources-backlog.md .ai/FIXME.md docs/adr/ADR-0014-resilient-scraping-concurrency.md spec/sources/games/
git commit -o .ai/tasks/sources-backlog.md .ai/FIXME.md docs/adr/ADR-0014-resilient-scraping-concurrency.md spec/sources/games/ -F - <<'EOF'
docs(sources): record the 2026-07-20 sweep — 4 prohibitions, 1 open conflict

Epic / Kickstarter / Gamalytic all challenge-wall robots.txt itself, so no
fetch grant can be established. MobyGames signals ai-train=no with an
express Article 4 reservation plus ClaudeBot Disallow — aimed at exactly
what OGIP publishes.

F9 records the unresolved one: steam_applist is enabled on a host whose
robots.txt disallows everything. Needs a human verdict.

ADR-0014's curl_cffi rung is marked speculative: the sweep found no
permitted source in this domain that needs it.

Refs: #19
EOF
```

---

### Task 4: Seed the glossary with the domain and governance vocabulary it lacks

`.ai/AI-glossary.{en,ru}.md` holds 12 entries, all infrastructure and agent-coordination. `metacritic`, `steam`, `wishlist`, `premium`, `concurrent` appear zero times. An agent joining this repo learns the lane-lock protocol and nothing about the business it serves.

**Files:**
- Modify (via the skill, never by hand): `.ai/AI-glossary.en.md`, `.ai/AI-glossary.ru.md`

- [ ] **Step 1: Add the governance terms established this session**

Invoke `/add-terms-to-glossary` (writer: `/update-terms-glossaries`). Do **not** hand-edit the glossary files — the skill owns their format, the quick-index table, and the anchor links, and a hand edit desynchronises the index.

Terms, each `[project]` marked, with the OGIP example that produced it:

| Term | The point |
|---|---|
| `do_not_fetch` vs `publishable` | two independent gates: one protects the *fetch*, the other the *republication*. robots.txt is permission to fetch, never permission to republish. |
| `Content-Signal: ai-train=no` | machine-readable rights reservation (EU Directive 2019/790 Art. 4) — blocks ML-dataset use even where crawling is allowed. MobyGames, 2026-07-20. |
| JSON-LD extraction contract | scrape schema.org markup, not visible CSS; select by `@type` because pages carry several `ld+json` blocks. Every `class=*metascore*` selector on Metacritic matches zero nodes after a rebuild. |
| `fetch_tier` escalation ladder | `httpx → curl_cffi → playwright`, escalate only on evidence; needing Playwright often means the site is saying no. |
| generated spec projection | `spec/sources/` is a one-way projection of an out-of-repo registry; hardlinking was measured unsafe because `git checkout` severs the inode. |
| source Definition of Done | connector + contract + staging model + config entry + fixture test + drift gate. A gate written as prose is a gate that gets skipped. |

- [ ] **Step 2: Add the business-domain terms**

These come from the Hushcrasher material (site, five newsletter posts, LinkedIn), read 2026-07-20. Definitions are the ones the material gives — do not substitute general games-industry framing.

| Term | Business definition (as given) |
|---|---|
| **scope** | Measurable game characteristics — playtime, 2D vs 3D, single vs multiplayer, genre tags, platform count, voiced audio. The dominant explanatory variable for budget. |
| **Kei** | Smallest tier; "what many would call 'solodev' games" — Undertale, Papers Please, Terraria. Median budget <$65k. |
| **Midi** | Small and medium studios — Hades, Valheim. ≈14× Kei. |
| **AA** | "Entry point for multi-million-dollar budgets"; hundreds of credited individuals. ≈33× Midi. |
| **AAA** | Thousands of contributors. ≈10× AA. |
| **indie** | **Explicitly rejected as an analytical category** — conflates aesthetics, financing, team size, IP ownership and creative intent. Evidence: a quarter of AAA games are self-published. |
| **credits length** | Count of credited individuals, excluding special thanks and playtesters. The single strongest scope signal. |
| **PPP** | Purchasing-power parity — what a basket of goods costs locally. Naive FX conversion overprices poorer markets. |
| **quantile budget estimate** | Output is a q10–q90 range, never a point estimate: "two studios making similar games rarely spend the same amount." |
| **horizontal vs vertical differentiation** | Small games compete on novel mechanics (horizontal); AA/AAA compete on more content and fidelity (vertical) — the driver of the cost spiral. |

**Flag the naming inconsistency rather than smoothing it over:** the public site uses *indie / triple-I / AA / AAA*, while the newsletter's formal "Classification System 1.0" uses *Kei / Midi / AA / AAA*. Same tiers, two vocabularies. Record the mapping (Kei ≈ indie/solodev, Midi ≈ triple-I) and pick one for OGIP's own prose.

- [ ] **Step 3: Verify both languages stayed in sync**

```bash
grep -c '^## ' .ai/AI-glossary.en.md .ai/AI-glossary.ru.md
```

Expected: equal counts, and every new EN entry has its RU twin. The RU file is the Russian-slang twin, not a literal translation — keep that register.

- [ ] **Step 4: Commit**

```bash
bash src/scripts/public-hygiene.sh
git add .ai/AI-glossary.en.md .ai/AI-glossary.ru.md
git commit -o .ai/AI-glossary.en.md .ai/AI-glossary.ru.md -m "docs(glossary): source-governance + business-domain vocabulary

The glossary had 12 entries, all infra and agent coordination — nothing
about the business this platform serves.

Refs: #19"
```

---

### Task 5: The business-domain documentation section

`docs/` describes the system in full and the *business* not at all. `docs/README.md` opens with one sentence of positioning and moves straight to architecture. Nothing states what questions this platform answers, or what any given source means to an analyst.

**Files:**
- Create: `docs/domain/README.md` (the business domain), `docs/domain/sources.md` (per-source business meaning)
- Modify: `docs/README.md` (index row)

Hard rule 8 requires a `README.md` per directory — `docs/domain/README.md` satisfies it and carries the domain overview, so no separate index file is needed. (FIXME **F4** already tracks six directories in breach; do not add a seventh.)

- [ ] **Step 1: Correct the domain framing before writing a word**

The material (hushcrasher.com, five newsletter posts, LinkedIn company page — all read 2026-07-20, all free and unpaywalled) does **not** support the framing this repo has been assuming.

The recurring axis is **production cost vs scope vs realised revenue**: what did it cost to build, what tier does that put it in, and what can it therefore earn. Pricing appears as **regional/PPP price ladders**, not discounting. **Wishlist conversion and discount-decay curves appear nowhere in the material** — do not write a section on them.

The consumer is not a generic "analyst": the stated customers are **studios, publishers, investors/VCs and M&A professionals**, and the stated service lines are pricing optimisation, pre-launch sales projection, commercial due diligence, and budget/scope benchmarking.

- [ ] **Step 2: Write `docs/domain/README.md`**

1. **What this platform is for** — the four decisions above, in business language, no tooling nouns.
2. **Who the consumer is** — studios, publishers, investors, M&A; what each does with the datasets.
3. **The recurring questions**, with the material's own findings as illustration:
   - budget estimation at scale (≈100k Steam titles modelled from ≈200 disclosed budgets, claimed within a 10% average margin);
   - cost-inflation decomposition — *"it doesn't cost more to make games. We just make bigger ones"*;
   - market saturation — median revenue per game fell 97% between 2012 and 2018;
   - competitive positioning by tier;
   - regional pricing power — *"adapting your prices to regional economic realities isn't charity. It is, first and foremost, a question of profit."*
4. **The five dimensions**, each with its business question and the material's monetised coefficients where it gives them:
   - **pricing** → realisable price ladder per market. Tier anchors: Kei a few dollars, Midi ≈$17, AA ≈$40, AAA ≈$60.
   - **scope/length** → how big is this game in comparable terms. Doubling playtime ≈ +24% budget; a 2D game is ≈32% cheaper than its 3D equivalent; multiplayer ≈ +20%; any voiced audio ≈ +70%.
   - **production budget** → what should this cost. Kei <$65k; Midi ≈14× Kei; AA ≈33× Midi; AAA ≈10× AA; publisher-backed titles cost 3–4× self-funded.
   - **traction/attention** → did it find an audience. The material uses **review counts as the revenue proxy** (≈25% of sales measured by review share) — this is the load-bearing use of traction data.
   - **quality** → does critical reception move commercial outcomes. **State honestly that the material barely supports this one**: critic scores are essentially absent from the five posts. OGIP's quality dimension rests on standard industry practice, not on this evidence. Marking that gap is more valuable than papering over it.
5. **Three dimensions the material treats as first-class that OGIP's five omit** — name them as candidate gaps, not as settled scope:
   - **team composition / headcount** — *"the strongest predictor of budget is team size"* (2× team ≈ +70% budget); management ratio is itself a scope signal (≈1 in 7 credited people in AAA);
   - **publishing model** — self-published vs publisher-backed is a 3–4× budget multiplier and an independent segmentation axis;
   - **time / vintage** — every post is a cohort comparison; without a vintage axis the other four dimensions are not comparable across years.
6. **Provenance** — sources and date, and which claims are the material's versus standard industry framing.

Correct one expectation on the way: LinkedIn was **fetched successfully**, no challenge wall. It confirmed a boutique games-industry market-research firm, founded 2024, 2–10 employees. Do not carry forward the assumption that it was unreadable.

- [ ] **Step 3: Write `docs/domain/sources.md`**

One or two sentences per source, in **business** language. Technical detail belongs in `spec/sources/`; do not duplicate it. Use these meanings:

| Source | What an analyst uses it for |
|---|---|
| RAWG | Cross-platform catalogue; the identity and genre spine for titles that never appear on Steam. |
| Steam applist | The universe definition — the denominator behind any "share of releases" or saturation claim. |
| Steam appdetails | The commercial fact sheet: price, genre, platform, language support, multiplayer. Feeds scope and pricing directly. |
| Steam appdetails (regional) | Observed price ladders per country — the empirical check against PPP-fair pricing. |
| Steam appreviews | The traction proxy standing in for units sold when revenue is undisclosed. |
| SteamSpy | Owner and playtime estimates; converts attention into rough units and revenue for competitive sizing. |
| SteamCharts | Concurrency over time: launch-window shape and post-release decay. |
| Metacritic / OpenCritic | Critical reception as the quality signal — the input to "does review quality predict commercial outcome". |
| IGDB | Structured metadata: genre, engine, franchise, involved companies. Supplies engine and studio/publisher attribution, both budget drivers. |
| PSN Store | Console-side pricing and catalogue; tests whether Steam findings generalise beyond PC. |
| Twitch | Streamer attention as a leading indicator of discovery and launch-window momentum. |
| Reddit | Community sentiment and pre-release interest, complementing structured traction data. |

Add a column for which of the five dimensions each source feeds, and mark **which sources cannot be republished** (`publishable: false` — Metacritic, OpenCritic, SteamCharts, PSN, IGDB, Twitch, Reddit). Those inform internal features but cannot reach the public datasets. For a business reader that is a product constraint, not a footnote.

- [ ] **Step 4: Write the coverage-gap section — the most important part of this doc**

The research surfaced a collision that no existing document states, and it is worth more than the rest of the section combined.

**The domain's two most load-bearing signals are both legally unavailable to OGIP.**

- **Credits length** — the single strongest scope signal in the methodology, and the basis of the team-size predictor (*"the strongest predictor of budget is team size"*). Its source is **MobyGames**, which OGIP does not register and, per the 2026-07-20 sweep, signals `Content-Signal: ai-train=no` with an express Article 4 reservation plus `User-agent: ClaudeBot / Disallow: /`.
- **Playtime** — a directly priced budget input (+24% budget per doubling). Its canonical source is **HowLongToBeat**, already registered `do_not_fetch: true` — robots/ToS prohibit automated retrieval and name AI/ML datasets as a prohibited use.

So the **production-budget dimension — the core of this domain — currently has no permitted primary input.** State it plainly, with both prohibitions linked, and record what remains: Steam-derived playtime proxies, IGDB `time_to_beat`, Wikidata CC0 dumps (`P2130` cost), and a licensed or permission-based route to credits data.

Note the one unclosed door honestly: MobyGames' `/info/api/` page returned 403 to automated fetch, so the **API's** terms — legally distinct from the site's content signals — were never read. A human reading them in a browser could reopen this. That is a concrete, cheap next action, not a dead end.

- [ ] **Step 5: Register the section in the docs index**

Add a row to the table in `docs/README.md`:

```markdown
| [domain/](domain/) | The business domain: what questions this platform answers, and what each source means to an analyst |
```

- [ ] **Step 6: Verify and commit**

```bash
bash src/scripts/public-hygiene.sh     # a public repo; the newsletter is a private company's material
bash src/scripts/check-md-refs.sh 2>/dev/null || true   # if the repo has a link checker, run it
git add docs/domain/ docs/README.md
git commit -o docs/domain/ docs/README.md -m "docs(domain): business-domain section + per-source business meaning

docs/ described the system fully and the business not at all.

Refs: #19"
```

Quote sparingly and attribute: the newsletter is a private company's material and this repository is public. Summarise the analytical framing; do not paste its prose.

---

### Task 6: Reconcile GitHub Issues with what actually shipped

**Files:** none in the repo — this task operates on `gh` and `.ai/tasks/`.

**Do not run a full `tasks-sync`.** It pushes every dirty task file, including other lanes' in-flight edits. Reuse its per-slug `_create`/`_update` path, one issue at a time.

- [ ] **Step 1: Close #18 and correct its scope**

[#18](https://github.com/dataengy/ogip/issues/18) is "Resilient scraping: `ScraperSource` + landing + first scraped source". What shipped is narrower than the issue: `ScraperSource`, `PoliteFetcher`, the Metacritic source, and (after Task 1) its contract and staging model. **Not** shipped: Postgres landing, idempotent upsert, watermarks, DLQ, circuit breaker, the parse pool.

Either close #18 and open a successor issue for the landing/resilience half, or narrow #18's title and body to what shipped and open the successor. Prefer the first — a closed issue that claims unbuilt work is worse than an extra issue. Update `.ai/tasks/scraping-resilient.md` to match whichever you choose; its deliverables checklist is currently all-unchecked despite several being done.

- [ ] **Step 2: Update #19 and clear FIXME F6**

[#19](https://github.com/dataengy/ogip/issues/19) is the sources backlog. FIXME **F6** records that its body has drifted from `.ai/tasks/sources-backlog.md`. Task 3 changes that file again, so re-sync the body from the task file and then delete the F6 entry from `.ai/FIXME.md` — the register's own rule is that an entry which becomes wrong is deleted, not left as archaeology.

- [ ] **Step 3: Open the blocking robots-verdict issue**

Title: `Decide: does api.steampowered.com robots.txt govern the documented Web API?`

Body states both readings and what each implies (strict → `steam_applist` is in breach and Steam Charts needs Playwright; documented-API → `steam_applist` is fine and Steam Charts is a plain `dlt` source), that it blocks any new work on that host, and that it needs a human verdict. Label `p1`. Cross-link F9 and #19.

- [ ] **Step 4: Open the MobyGames API-terms issue**

Title: `Read the MobyGames API terms by hand — the budget dimension depends on it`

The domain's strongest budget predictor is credits length, and its source is MobyGames, whose site-level `Content-Signal` reserves rights against exactly what OGIP publishes. But the **API terms were never read** — `/info/api/` returns 403 to automated fetch. This is a ten-minute human task with a large payoff: it either reopens the production-budget dimension or closes it definitively.

Body records both prohibitions (MobyGames site signals, HLTB `do_not_fetch`), states that production budget currently has **no permitted primary input**, and lists the fallbacks to evaluate if the API is also closed: IGDB `time_to_beat`, Wikidata CC0 dumps (`P2130`), Steam-derived playtime proxies. Label `p1`. Cross-link #19.

- [ ] **Step 5: Verify**

```bash
gh issue list --limit 30 --state open
gh issue view 18
```

Expected: #18 reflects reality, the successor issue exists, both new issues (robots verdict, MobyGames API terms) exist, and no issue claims work that has not shipped.

---

## Automation: what to script, what to reuse, what not to build

The brief asked for skills or — preferably — scripts covering all of the above. The honest answer is that **most of this is already automated and only one new artifact is warranted**. Skills are expensive to maintain and this catalog already has ~700; adding one per workstream would be the wrong instinct.

| Workstream | Verdict | Why |
|---|---|---|
| Source DoD gate | **NEW: `.ci/steps/source-dod.sh` + prek hook** (Task 2) | The one real gap. A rule that only exists in prose was demonstrably skipped. This is a check, so it must be code — and it belongs in `.ci/steps/` so CI and local runs execute identical bytes. |
| Registry / forbidden entries | **Reuse** — `just sources-probe-all` · `sources-route` · `sources-drift`, and `/add-data-source` (now with Step 0 + the DoD checklist) | Already deterministic and already Justfile-wrapped. Writing a source entry is judgment work — evaluating verbatim licence text — and does not become more correct by being scripted. |
| Glossary | **Reuse** — `/add-terms-to-glossary`, writer `/update-terms-glossaries` | It already owns the file format, the quick-index table and the anchors, and it already has extracted scripts (`scripts/glossary_writer.py`) plus tests. Nothing to add. |
| Domain docs | **Reuse** — `/upsert-doc-about` | One-off prose. Automating a document written once is cost without payoff. |
| GitHub Issues | **Reuse** — the per-slug `_create`/`_update` path inside `tasks-sync` | Deliberately *not* wrapped in a new convenience command: the full `tasks-sync` is the hazard (it pushes other lanes' dirty task files), and a friendlier wrapper would make the dangerous path easier to reach. |
| Skill-copy drift | **NEW, but tiny: a `SessionStart` hook** — see below | A silent failure class, discovered this session. |

**The one additional thing worth building.** `~/.claude/skills/add-data-source/skill.md` was a stale independent copy, three days behind the catalog — so `/add-data-source` had been *executing an old version* with no symptom. `skill-sync-state` detects this, but only when someone thinks to ask. A `SessionStart` hook running the equivalent of `just -f "$JF" status` and reporting only the STALE rows converts a silent failure into a one-line notice. Scope it to reporting; a hook that silently re-links files during session start would be a worse bug than the one it fixes.

**On `/save-all-deterministic-for-skill-as-scripts`:** it applies to the `/add-data-source` update already made, and the additions there were placeholder-bearing examples (`<target paths>`, `<key>`) rather than runnable logic, so there is nothing new to extract. Run it against the skill anyway before the next release to confirm — and note that the skill's *pre-existing* inline blocks are out of scope here; refactoring another skill's body is not this plan's work.

## Deliberately not in this plan

- **The Postgres `landing` sink (ADR-0006 path B).** Scoped out by the user for this slice; `ScraperSource` already emits `content_hash` as the upsert identity, so the interface is ready when it returns.
- **Steam Charts via Playwright.** Blocked on the F9 robots verdict. Building it before that ruling would mean shipping a Playwright tier that a one-line answer could make unnecessary.
- **The `ingestion/README.md` deletion** currently uncommitted in the working tree. It belongs to another lane and is a hard-rule-8 breach; it is a handoff, not this plan's work.
