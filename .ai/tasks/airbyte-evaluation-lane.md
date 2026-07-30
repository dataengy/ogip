# Task — Airbyte + Terraform evaluation lane (anchor: github_repos; negative-result by design)

**Status:** 🚧 in progress · **Priority:** P3 (backlog) · **Issue:** [#41](https://github.com/dataengy/ogip/issues/41)

Lane: `airbyte` (claim `obj--airbyte` before writing). Everything lives in
`experimental/ingestion/airbyte/` — **off the `make` path**. Design SSoT:
[`docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md`](../../docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md) ·
plan: [`docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.md`](../../docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.md) ·
techdebt: [`docs/techdebt/airbyte-lane.md`](../../docs/techdebt/airbyte-lane.md).

## What this is

An **evaluation** of Airbyte + Terraform on its single best case — **not** production ingestion.
The domain re-read (cost × scope × revenue) found **zero** managed connectors fitting the product
sources; product ingestion stays **dlt**. Deliverable: a *measured* comparison of three Terraform
driver variants (yamldecode / codegen-`.tf` / codegen-`.tfvars`) over one shared
`modules/airbyte-connection`, plus an honest verdict.

## Anchor source

`github_repos` via `airbyte/source-github` 2.1.37 — the only connector in the 591-source OSS
registry that is certified **and** real code **and** public-data. `source-twitch` does not exist
(→ in-house declarative connector); `source-reddit` is community/manifest-only (counter-example).
Comparison: [`docs/comparisons/github_repos-ingestion-dlt-vs-airbyte-vs-custom.md`](../../docs/comparisons/github_repos-ingestion-dlt-vs-airbyte-vs-custom.md).

## Checklist

- [x] Design spec, implementation plan, techdebt tracker, comparison doc
- [x] `airbyte_emit.py validate` — real, green vs the live registry; negative-tested
- [x] Pre-commit gate `src/scripts/airbyte-blocks-check.sh`
- [x] Phase 0 — `lane/airbyte` worktree; `services.airbyte_port` + `postgres.airbyte_schema`
      in the config SSoT; `experimental/ingestion/airbyte/` scaffold
- [x] Phase 1 scripts (`up`/`down`/`credentials.sh` + Justfile) — **runtime NO-GO on this
      machine**, see techdebt (abctl disk-exhausted mid-install; premise unverified)
- [x] Phase 2 — shared `modules/airbyte-connection`, provider 1.2.0, schema-verified, validate-green
- [~] Phase 3 — Variant A (yamldecode `for_each`): HCL **validate-green offline** and console-proven
      to discover github_repos+reddit_posts, build github's 6 streams, parse the repo from the
      descriptor url. `plan`/`apply` (the *measured* datapoint) blocked on the runtime.
- [ ] Phase 4 — Variants B & C; removes the `render` stub; drift gate
- [ ] Phase 5 — Twitch declarative connector
- [x] Phase 6 — CI `airbyte-tf` job (`fmt`+`validate`; `plan`/`apply` never — no reachable API)
- [ ] Phase 7 — finish `/add-airbyte-sync` deploy; README with the **measured** verdict

## Gates that bite

- **abctl needs ≥10 GiB free** (k8s-in-docker). Re-check before Phase 1.
- Phase 1 is the real go/no-go: if abctl + provider 1.2.0 do not talk, the runtime premise fails —
  surface it, do **not** fall back to the removed compose-v0.63.
- `airbyte_emit.py render <a|b|c>` is a **loud stub (exit 2)** until the TF module exists —
  defer-don't-fake, tracked in techdebt, never a silent no-op.

<!-- ogip-task: airbyte-evaluation-lane -->
