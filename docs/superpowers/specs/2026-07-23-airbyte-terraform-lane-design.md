# Airbyte + Terraform ingestion lane — design

- **Date:** 2026-07-23
- **Status:** design, awaiting approval
- **Lane:** `experimental/ingestion/airbyte` (off the production `make` path — AGENTS.md §30-32)
- **Refs:** OGIP#18, OGIP#19

## 1. Problem

`spec/sources/games/*.yaml` descriptors may carry an `airbyte:` block declaring that a source
should be ingested by Airbyte rather than dlt. Nothing consumes those blocks. This design turns
them into a running, Terraform-managed Airbyte deployment — and, in doing so, tests the claim the
blocks assert: *that a maintained connector beats hand-rolling dlt*.

## 2. Evidence that reshaped the design

All verified live against `https://connectors.airbyte.com/files/registries/v0/oss_registry.json`
(591 sources, 59 certified / 532 community) on 2026-07-20 and re-verified 2026-07-23.

**2.1 — Airbyte OSS no longer supports docker-compose.** The file was *removed* from
`airbytehq/airbyte-platform` by `refactor: remove docker compose configuration (#13544)` on
2024-08-23; the repo is actively developed (last push 2026-07-19), so there is no maintained-but-
frozen compose path. Supported self-host paths are `abctl` (kind + Helm inside Docker) and Helm on
a real cluster — **both end in Kubernetes**. The last shipped compose (`v0.63.14`) still runs but
freezes the platform at 08.2024, predating the `/api/public/v1` endpoint the current Terraform
provider targets.

**2.2 — The Terraform provider was rewritten.** v0.x had 278 per-connector resources
(`airbyte_source_reddit`, …). v1.x has **8 resources total**: every source is a generic
`airbyte_source` with a `definition_id` and a JSON `configuration` string. This is *better* for us
— one resource with `for_each` over a map derived from YAML is now natural, which was structurally
impossible before. Pin **1.2.0** (1.3.0 exists only as `-rc1`).

**2.3 — `source-twitch` does not exist.** Zero hits at any support level, and none in the old
278-resource provider either. The descriptor's `connector: source-twitch` was a fiction; it has
been corrected in the registry SSoT to an in-house declarative connector.

**2.4 — `source-reddit` is hollow.** `language: manifest-only`, `releaseStage: alpha`, v0.0.57,
community. *Manifest-only means the connector is itself just a declarative YAML* — there is no
engineering embedded in it that dlt's `rest_api` does not equally provide. The maintained-connector
argument is not weak here, it is empty.

**2.5 — The certified pool is structurally mismatched with OGIP.** Of 59 certified connectors,
nearly all extract from a SaaS account *you own* (Salesforce, Stripe, HubSpot, Zendesk, ad
platforms) or from your own database. OGIP ingests **public** market data. `source-github` is the
exception: GitHub's public data *is* the product. It is `language: python`,
`releaseStage: generally_available`, certified, v2.1.37.

**2.6 — "Certified" measures support commitment, not implementation depth.** Certified splits by
implementation language as **39 manifest-only · 11 python · 9 java**. A manifest-only connector is
a declarative YAML — it embeds no engineering that dlt's `rest_api` does not equally provide, and
`source-airtable`, `source-google-sheets`, `source-typeform` are all in that bucket despite being
certified. So the pool that is *both* certified and real code is **20 of 591 (3.4%)**. Of the 11
certified Python sources, five are file/blob readers (`s3`, `gcs`, `azure-blob-storage`,
`google-drive`, `file`) and five are own-account SaaS (`facebook-marketing`, `google-ads`,
`salesforce`, `shopify`, `sharepoint-enterprise`). **`source-github` is the only certified,
real-code connector in the entire registry that reads public data.** That is the whole reason it is
the lane's anchor — not domain centrality.

**2.7 — The target domain has zero connector coverage.** Searched the registry for every source the
domain actually runs on: **Steam, MobyGames, Gamalytic, SteamDB, HowLongToBeat, IGDB, itch.io,
Epic, GOG, PlayStation, Xbox, Nintendo, Kickstarter — zero hits, at any support level.** Games
market intelligence is public-web data reached by API and scraping, which is precisely the shape
Airbyte does not serve. This is a structural property of the domain, not a gap Airbyte will close.

## 3. Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Runtime = `abctl` | The only supported path yielding a platform the v1.x provider can talk to. Compose-v0.63 and k3s+Helm get tracked issues, not implementations. |
| D2 | Destination = own Postgres schema `airbyte_raw` | Same instance as the dlt landing (ADR-0006), separate schema — the experimental lane never writes into the production landing zone. |
| D3 | Three Terraform driver variants, one shared module | The comparison is the deliverable; a winner is chosen after they exist. |
| D4 | Provider pinned `airbytehq/airbyte` 1.2.0 | 1.3.0 is a release candidate. |
| D5 | `definition_id` is never stored in specs | Resolved live via the `airbyte_connector_configuration` data source. Same principle as `spec/sources/README.md:16-18` — a stored verdict rots into a lie, and so does a stored UUID. |
| D6 | Twitch ships as an in-house declarative connector | No registry connector exists; registered via `airbyte_declarative_source_definition`, so it stays fully Terraform-managed. |
| D7 | Isolation via **git worktree**, not a branch switch | See §8 — this checkout is shared by 4+ live sessions. |

## 4. The source set

Three sources, deliberately spanning the full quality range — which makes the lane a real test
rather than a demo:

| Source | Connector | Support | What it proves |
|---|---|---|---|
| `github_repos` | `airbyte/source-github` 2.1.37 | **certified**, Python CDK, GA | The genuine case — see §4.1. Domain fit: game-engine ecosystem activity (Godot/Bevy/O3DE + modding long tail) — engine is a literal input to the cost×scope×revenue models. |
| `reddit_posts` | `airbyte/source-reddit` 0.0.57 | community, manifest-only, alpha | The counter-example. Kept *because* it is weak: it demonstrates that "there is a connector" is not by itself an argument. |
| `twitch_streams` | in-house declarative manifest | n/a — we maintain it | The custom-connector path (`airbyte_declarative_source_definition`), and the honest admission that lane uniformity — not maintenance savings — is the only remaining benefit. |

### 4.1 Why `source-github` is the one that earns the lane

Verified against <https://docs.airbyte.com/integrations/sources/github> on 2026-07-23:

- **39 enumerated streams**, 26 of them incremental. (The page's own summary header says 53 —
  the enumeration and the header disagree; 39 is what is actually listed. Either number is an
  order of magnitude past what a hand-rolled client stays cheap at.)
- **Mixed REST + GraphQL.** The `releases` stream goes through GraphQL while most others are REST.
  Hand-rolling means implementing *two* API paradigms and their two pagination models.
- **Multi-token rotation** with client-side throttling: the connector rotates through several PATs
  and waits out rate limits (configurable, up to 240 min) rather than failing the sync.
- **Per-repo incremental state** across a repo list — N repos × M streams of cursor bookkeeping.
- **OSS caveat:** Open Source supports **PAT only**; OAuth is Cloud-only. Matches our
  `GITHUB_TOKEN` slot, so no design change — but it is not the same auth story as Cloud docs imply.

None of this is expressible in dlt's declarative `rest_api`; it would become a typed client we own
and maintain. That is the exact cost the `airbyte:` blocks claim to avoid, and here the claim holds.

## 5. Architecture

```
experimental/ingestion/airbyte/
  up.sh / down.sh                  abctl local install/uninstall; port from config SSoT
  credentials.sh                   abctl local credentials → AIRBYTE_CLIENT_ID/SECRET
  connectors/twitch/manifest.yaml  low-code declarative connector for Helix
  terraform/
    modules/airbyte-connection/    airbyte_source + airbyte_connection (+ one shared destination)
    variant-a-yamldecode/          fileset() + yamldecode() over spec/ — zero generation
    variant-b-codegen-tf/          generated .tf, committed
    variant-c-codegen-tfvars/      generated .tfvars.json + hand-written HCL
  README.md                        the three-variant comparison
```

Only *how config reaches the module* differs between variants; the resource definitions are shared.
Otherwise the comparison is dishonest and the HCL triplicates.

**Auth.** OSS uses client credentials with a **15-minute** token TTL, so the provider gets
`client_id`/`client_secret`/`token_url` — never a static `bearer_auth`, which can expire mid-apply.

**State.** Local file under `.run/`. This is an experimental lane; a remote backend is unwarranted.

**Layer naming** (AGENTS.md hard rule 1): `github__repos`, `reddit__posts`, `twitch__streams` in
`airbyte_raw`.

**Config SSoT.** `config/config.yml` gains `services.airbyte_port` and `postgres.airbyte_schema`;
values reach the stack through the rendered `.env` (`make render-env`). No literals in scripts.

## 6. Scripts, gates, skill

Scripts land in the **existing** `~/.ai/skills/_scripts/de/ingestion/` submodule beside
`route_tool.py` (which already assigns the `airbyte` route) — not a new domain.

- `emit_airbyte_tf.py` — validates `airbyte:` blocks (connector exists in the live registry ·
  `incremental` ⇒ `cursor` present · `streams` non-empty) and renders artifacts for variants B/C.
- `src/scripts/airbyte-drift.sh` — drift gate, modelled on `sources-registry-check.sh`.
- Root `Justfile` passthroughs in the `sources-*` style (`Justfile:177-188`): `airbyte-up`,
  `airbyte-tf-validate`, `airbyte-tf-plan`, `airbyte-apply`, `airbyte-drift`.
- `.ci/steps/airbyte-tf.sh` + a pre-commit hook firing only when `spec/` or `terraform/` is touched.
- Skill `/add-airbyte-sync`, created via `/create-skill`; all deterministic steps behind the
  Justfile per `/save-all-deterministic-for-skill-as-scripts`.

## 7. What CI can and cannot verify

An earlier statement in this design's discussion promised `terraform plan` in CI. **That was
wrong** and is corrected here: `plan` requires a reachable Airbyte API, so it cannot run
credential-free in CI.

| Gate | Runs | Verifies |
|---|---|---|
| CI (every PR) | `terraform fmt -check`, `terraform validate`, `airbyte-drift` | HCL is well-formed; generated artifacts match `spec/`; `airbyte:` blocks are internally valid |
| Local, opt-in | `airbyte-tf-plan`, `airbyte-apply`, real sync | Connector definitions resolve; credentials work; data actually lands |

The local path skips cleanly when credentials are absent — it never fails as if broken.

## 8. Isolation — worktree, not branch switch

This checkout is shared by 4+ live agent sessions committing to `dev` (session start reported 28
live agent processes and a held repo lock). `git checkout -b` would move the working tree **for
every one of them**. So: a dedicated **git worktree** plus an `obj--airbyte` lane lock. Subtree is
not used — the Terraform reads `spec/sources/games/*.yaml` from above its own prefix, so a vendored
subtree would not be self-contained, and closing that gap would mean a second projection layer on
top of the registry→`spec/` one that already exists.

## 8a. What this lane is actually for

A domain re-read (Hushcrasher's site + newsletter archive, 2026-07-23) changed why this lane is
worth building — not what it builds.

Their published method rests on: Steam (~100k games), **MobyGames** credits, **SteamDB** release
stats, **Gamalytic** revenue estimates, plus budget ground truth scavenged from "web archives, news
articles, data leaks, post-mortems, and forums" and a developer-submission channel. The model's
stated drivers are *"credit length and disk size, far outweighing all the other metrics"*, plus
distinct job titles, supported languages, and publisher/studio experience.

None of those sources has an Airbyte connector (§2.7). Their engineering framing is explicit that
the work is *"writing Python ingestion pipelines (API + scraping) into an analytical lake — not
wiring managed connectors"*.

So the lane's deliverable is **a documented, evidence-based tool evaluation with a negative
result**, and `github_repos` exists to make that evaluation *real rather than theoretical*: one
connector actually deployed and syncing, so the conclusion rests on a measurement instead of an
opinion. The lane must therefore stay visibly in `experimental/` and be framed as an evaluation
everywhere it is described. Presenting it as ingestion infrastructure would misrepresent both the
evidence and the architecture.

Corollary for the ingestion lane (not this one): **Gamalytic is absent from the source registry**
and is a named revenue-estimate source in the domain. Worth a descriptor. Handed off, not actioned
here.

## 9. Risks

- **The lane's premise survives on one source.** Strip `github_repos` and no remaining source
  justifies Airbyte over dlt. That is a finding worth stating plainly in the README, not hiding.
- **Variant B is expected to lose.** Generated `.tf` in git reproduces exactly the drift class the
  registry→`spec/` projection already suffers. It is still built, because a predicted result is not
  a measured one — but the prediction is on record.
- **`abctl` runs Kubernetes-in-Docker.** Heavier than the rest of the compose-based stack, and it
  does not join the `ogip` network the way `deploy/obs/` does. Disk and memory cost is real.
- **`source-github` rate limits.** Keyless is 60 req/hr (measured); a real sync needs
  `GITHUB_TOKEN` for 5,000/hr.

## 10. Out of scope

Publishing any of this data (all three sources are `publishable: false`); promoting Airbyte to the
default `make` path; staging/core models over `airbyte_raw`; a remote Terraform backend.
