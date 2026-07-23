# Airbyte evaluation lane — implementation plan

- **Date:** 2026-07-24 · **Refs:** OGIP#18, OGIP#19
- **Design SSoT:** `docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md`
- **Techdebt tracker:** `docs/techdebt/airbyte-lane.md`
- **Anchor source:** `github_repos` (`airbyte/source-github` 2.1.37 — certified, Python CDK, GA)
- **Isolation:** worktree `OGIP.worktrees/airbyte` on `lane/airbyte` + `obj--airbyte` lock
  (the repo's existing convention; NOT a branch switch on the shared checkout)

## Purpose (do not lose this framing)

This lane **evaluates** Airbyte on its single best case; it is not production ingestion. Product
ingestion of github goes via dlt (`docs/comparisons/github_repos-ingestion-dlt-vs-airbyte-vs-custom.md`).
Success = a working, measured comparison of three Terraform drivers + an honest verdict, with one
connector actually syncing. Everything stays in `experimental/`, off the `make` path.

## Preconditions

- Disk ≥ 10Gi free (abctl runs k8s-in-docker). **Currently 5Gi — `/clean-disk` first.** Hard block.
- `GITHUB_TOKEN` present (keyless is 60 req/hr; real sync needs 5,000/hr).
- Docker/colima running.

## Phase 0 — Lane setup & config

1. `git worktree add OGIP.worktrees/airbyte -b lane/airbyte origin/dev`; claim `obj--airbyte` lock.
2. `config/config.yml`: add `services.airbyte_port: 8000` and `postgres.airbyte_schema: airbyte_raw`;
   map both in `config/.env-render.py`; `make render-env`.
3. Scaffold `experimental/ingestion/airbyte/{terraform/,connectors/,README.md}`.

**Verify:** `make render-env` emits the two new vars; tree matches the spec §5.

## Phase 1 — Runtime (abctl) + destination

1. `up.sh` / `down.sh` wrapping `abctl local install` / `uninstall` (port from SSoT).
2. `credentials.sh` → `abctl local credentials` → write `AIRBYTE_CLIENT_ID/SECRET` to `.env`.
3. Create the `airbyte_raw` schema in the shared Postgres (idempotent DDL).
4. Root `Justfile` passthrough: `airbyte-up`, `airbyte-down`.

**Verify:** `curl localhost:8000/api/public/v1/health` OK; client-credentials token mints; a
manual UI source→dest→connection for github syncs one stream into `airbyte_raw`. **Gate: STOP** —
if the manual sync fails, the compose-vs-abctl assumption is wrong; report, do not paper over.

## Phase 2 — Shared Terraform module

1. `terraform/modules/airbyte-connection/`: `airbyte_source` (generic, `definition_id` via the
   `airbyte_connector_configuration` data source — never stored) + one shared `airbyte_destination`
   (postgres → `airbyte_raw`) + `airbyte_connection` (`configurations.streams`, `cursor_field` as a
   list, `primary_key` as list-of-lists).
2. Provider pinned `airbytehq/airbyte 1.2.0`; auth = client credentials; state = local file in `.run/`.

**Verify:** `terraform init` + `validate` green in a throwaway root that calls the module once for github.

## Phase 3 — Variant A (yamldecode) — expected winner

1. `variant-a-yamldecode/`: `fileset()`+`yamldecode()` over `spec/sources/games/*.yaml`, filter to
   entries with an `airbyte:` block, `for_each` the module.
2. `airbyte-tf-plan` / `airbyte-apply` root passthroughs (opt-in, credential-gated).

**Verify:** `plan` shows exactly the 3 airbyte sources; `apply` creates them; github connection runs
an incremental sync; `stargazers`/`releases` land in `airbyte_raw`. This is the measured datapoint.

## Phase 4 — Variants B & C (for the comparison)

1. Implement `airbyte_emit.py render b` (per-source `.tf`, committed) and `render c`
   (`connections.auto.tfvars.json` + hand-written HCL). Removes the render stub (techdebt row).
2. `variant-b-codegen-tf/` + `variant-c-codegen-tfvars/` consume the rendered artifacts.
3. Drift check: re-render, `git diff --exit-code` — wire into `airbyte-blocks-check.sh`'s scope.

**Verify:** all three variants `plan` to the *same* resource set for github; the drift gate fails on
a hand-edited generated file (negative-tested, per verify-gate-actually-covers).

## Phase 5 — Twitch declarative connector

1. `connectors/twitch/manifest.yaml` — low-code Helix (OAuth2 client-credentials, streams
   `streams`,`games`, `full_refresh`).
2. Register via `airbyte_declarative_source_definition` in the module.

**Verify:** connector registers; a Twitch snapshot lands. (Reddit stays as the community
counter-example — no extra work.)

## Phase 6 — Gates & CI

1. `.ci/steps/airbyte-tf.sh`: `terraform fmt -check` + `validate` on all three variants (no API).
2. `airbyte-blocks-check.sh` already gates the blocks; extend CI to run `fmt`/`validate`/drift.
   `plan`/`apply` remain local-only (documented limitation, not debt).

**Verify:** CI green on a PR touching `terraform/`; passes without credentials or a reachable API.

## Phase 7 — Skill completion + the deliverable

1. Finish `/create-skill` steps 13-15 for `/add-airbyte-sync` (hardlink to `~/.claude/skills`,
   sync targets, INDEX) — now that `render`/`apply` are real.
2. Write `experimental/ingestion/airbyte/README.md`: the three-variant comparison with the
   **measured** verdict (expected: Variant A wins — zero codegen drift), and the honest negative
   result (github is the only source that justified any of this; observability + runtime weight +
   the client's "not wiring managed connectors" keep it out of prod).

**Verify:** README states a verdict backed by Phase 3-4 measurements, not a prediction.

## Risks / stop conditions

- Phase 1 gate is the real go/no-go: if abctl + provider 1.2.0 do not talk, the whole runtime
  premise fails — surface it, do not force compose-v0.63.
- Disk: abctl is heavy; re-check free space before Phase 1.
- Lane discipline: push via throwaway worktree if the shared checkout collides
  ([[ogip-shared-checkout-worktree-push]]).
