# `/add-data-source` — Skill Decomposition Proposal

> **Status: PROPOSAL — gated.** No skill is created by this document. Creation runs through
> `/propose-skill-for-that` → `/create-skill` → `/save-all-deterministic-for-skill-as-scripts`
> per the standing skill-creation policy (skill files are never hand-written).

**Goal:** turn `/add-data-source` from a 243-line monolith into a chain whose members are
individually callable, and close the four capability gaps the catalog does not cover.

**Method:** `/split-skill-on-subskills` steps 1–3 (identify → audit for overlap → decide the
split shape). Steps 4–6 (create → refactor parent → sync) are the gated part.

---

## 1. Audit: what already exists

Searched all 521 catalog skills. **Reuse beats creation in six of the requested areas.**

| Requested capability | Existing skill | Verdict |
|---|---|---|
| Upsert ODCS for a source | **`/generate-odcs-specs`** (`de/contracts/`) | **REUSE.** A complete ODCS v3 authoring skill already exists, and it already names `spec/contracts/<source>/<name>.odcs.yaml` and the Layer-0 `<system>__<table>` contract. Nothing to create. |
| Research source + route to engine | **`/find-sources-and-match-tool`** (`de/ingestion/`) | **REUSE.** Already the extracted Steps 0–2 of the parent, with the 8-verdict router. |
| dlt "Prefect-related" | **`/integrate-sql-tool-with-prefect`** | **PARTIAL** — covers per-engine *transform* flows, not ingestion. Reuse the flow/asset pattern, don't restate it. |
| dlt "Dagster-related" | **`/add-dagster-module`**, `/add-dagster-odp-module`, `/integrate-dagster-with-dbt` | **PARTIAL** — same shape. |
| dlt under Dagster under Prefect | **`/call-dagster-from-prefect`** | **REUSE** verbatim. |
| Staging model SQL | **`/generate-agnostic-bruin-sql-specs`**, `/spec-compile-engines` | **REUSE.** |
| Run e2e and ship on green | **`/e2e-ship`**, `/dagster-e2e-run` | **REUSE.** |
| Prove a test/gate actually fails | **`/verify-gate-actually-covers`** | **REUSE** — this is the "is my new CI gate real" answer. |
| Business description / profit potential | — | **GAP** |
| Pipeline design source → landing → staging | — | **GAP** |
| Synthetic data generation | — | **GAP** — zero hits for `synthetic data\|fixture generat\|mock data\|faker` across all 521 skills |
| Per-engine connector authoring | — | **GAP** — the router *decides* the tool; nothing *implements* per tool |
| Author + debug per-stage tests, wire to CI | — | **GAP** (partially covered at the edges by the two reuse rows above) |

### The one place the literal ask should be refused

The request asks for five dlt skills: *native / standalone / Dagster-related / OpenDBT-related /
Prefect-related*. **Recommend one `/write-ingestion-dlt` instead**, because those five are two
different axes wearing one name:

- *native vs standalone* is a **packaging** axis — same `dlt.resource`/`dlt.pipeline` code, different
  entry point.
- *Dagster / OpenDBT / Prefect* is a **hosting** axis, and `de/orchestration/` already owns it in
  four skills.

Five dlt skills would each restate the same resource-and-pipeline authoring, then drift apart —
precisely the `split-skill-on-subskills` guardrail *"do not leave provider-specific logic
duplicated in both parent and subskill"*. One dlt skill with a **"where it runs"** section that
delegates by name to the existing orchestration skills carries the same information and has one
place to fix.

The per-engine split **is** justified across *different* engines: dlt's `RESTAPIConfig`, ingestr's
CLI invocation, Airbyte's connector config, and a scraper's politeness/JSON-LD contract share
essentially nothing. That is real divergence, not duplication.

---

## 2. Proposed split shape

**The cut follows the router's own vocabulary.** `/find-sources-and-match-tool` already emits one
of eight verdicts (`dlt · ingestr · airbyte · scraping · complex_api · spark · gcp · none`). One
implementer per *live* verdict makes the boundary principled rather than taste-based, and makes
routing executable end-to-end: `route <key>` names the skill that builds it.

`spark` and `gcp` are reserved with no registry precedent; `none` means FORBIDDEN. **No skills for
those three** — three skills nothing would invoke.

### New skills — 10 total, in three waves

#### Wave 1 — the gaps blocking OGIP today (3)

| Slug | Area | Purpose | Why it is not a section of the parent |
|---|---|---|---|
| `describe-source-business-value` | `de/ingestion` | Business description, usage scenarios, profit potential, and **which model dimension the source unlocks**. Writes a `business:` block into the registry entry and a row into `docs/domain/sources.md`. | Called *before* any code, often for sources that are never built. Answers "should we?", which the parent assumes has been answered. |
| `design-source-pipeline` | `de/ingestion` | Source → landing → raw → staging design, **plus the per-stage test plan**: what each stage must be tested against and which fixtures it needs. Produces the design the implementer skills consume. | This is where synthetic-data questions are *answered*; generation is a separate, later step. Design outlives any one engine choice. |
| `generate-synthetic-fixtures` | `de/testing` *(new area)* | Deterministic, **contract-driven** fixtures generated from the ODCS contract — seeded, no runtime randomness in committed files. Enforces the fixture-size/LFS law. | Zero catalog coverage, and useful far beyond ingestion (transform, DQ, e2e all need it). |

#### Wave 2 — the implementers, one per live router verdict (5)

`write-ingestion-dlt` · `write-ingestion-ingestr` · `write-ingestion-airbyte-oss` ·
`write-ingestion-scraping` · `write-ingestion-complex-api`

Each takes a probed + routed + contracted source and produces the connector. Each is entered
**only** via its router verdict. Shared laws (Layer-0, SSoT config, fixture-size/LFS) stay in the
parent and are referenced, never copied — the parent remains the one place they are stated.

`write-ingestion-dlt` additionally carries the **"where it runs"** section: standalone script ·
Dagster asset (`/add-dagster-module`) · Prefect flow (`/integrate-sql-tool-with-prefect`) ·
Dagster-inside-Prefect (`/call-dagster-from-prefect`). Delegation by name, no restatement.

#### Wave 3 — tests and the chain (2)

| Slug | Area | Purpose |
|---|---|---|
| `author-pipeline-stage-tests` | `de/testing` | Create / run / **debug** the per-stage unit tests and the final e2e, then wire them into CI. Hands the "does this gate actually fail on the real defect" question to `/verify-gate-actually-covers` rather than re-deriving it. |
| `onboard-data-source` | `de/ingestion` | **The chain / orchestrating skill.** business → find+route → ODCS → design → implement(verdict) → fixtures → tests → CI → ship. One command replaces knowing nine skills and their order. |

**Wave 3 must come last.** An orchestrating skill that names skills which do not yet exist is a
broken skill that reads as a working one.

### What `/add-data-source` becomes

Not deleted, not an umbrella. It keeps: the preconditions (lane lock, read the target's rules),
Step 0 (already built?), Step 3 (**the legality gate — blocking, and it must not move**), the three
laws, the Definition of Done, and Step 6 (ship). It **delegates** Steps 1–2 (already extracted),
contract authoring (`/generate-odcs-specs`), design, implementation, fixtures, and tests.

It becomes the *scaffold-and-ship* member of the `onboard-data-source` chain — which is what it
actually is today, minus the parts it inlines.

---

## 3. Scripts, not skills

Per the standing preference for a script over a skill wherever the step is deterministic:

| Need | Verdict |
|---|---|
| Definition-of-Done enforcement | **Script** — `.ci/steps/source-dod.sh`, already fully specified in the sibling plan `2026-07-20-source-dod-registry-and-domain-docs.md` Task 2. Do not also make it a skill. |
| Validate the registry `business:` block | **Extend an existing script** — add the field check to `just -f "$JF" split-check`. No new artifact. |
| Fixture generation itself | **Script** under `~/.ai/skills/_scripts/de/testing/`, wrapped by a Justfile recipe; `generate-synthetic-fixtures` is the judgment layer over it. This is the shape `/save-all-deterministic-for-skill-as-scripts` would produce anyway — build it that way from the start. |
| Skill-copy drift detection | **Hook** — the `SessionStart` reporter already proposed in the sibling plan. Report only; a hook that silently re-links files during session start is a worse bug than the one it fixes. |

No other new hooks. Each of the ten skills above must run
`/save-all-deterministic-for-skill-as-scripts` before its sync gate — mandatory, not optional.

---

## 4. Honest cost note

Ten new skills against a 521-skill catalog is a real increase, and the session that proposes them
is not the session that maintains them. Two mitigations are built in above: **six requested
capabilities collapsed into reuse**, and **five requested dlt skills collapsed into one**. Without
those, the literal reading of the request produces sixteen.

If only one wave is ever built, build **Wave 1** — those three are the ones with zero catalog
coverage and a live OGIP consumer.
