# Techdebt — Airbyte evaluation lane

One row per deferred item, each with the condition that unblocks it. Pattern rationale:
`~/.ai/skills/.settings/code_specs/script_standards.yml#deferred_functionality` — mark loudly,
never fake. Design SSoT: `docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md`.

| Item | State | Unblock condition |
|---|---|---|
| `airbyte_emit.py render <a\|b\|c>` | loud stub, exits 2 | The `experimental/ingestion/airbyte/terraform/modules/airbyte-connection` module exists. |
| Skill `/add-airbyte-sync` deploy | at review gate — agents-hub symlink only; NOT hardlinked to `~/.claude/skills`, not synced to other targets | The lane is built and `apply`/`render` are real; then finish `/create-skill` steps 13-15 (hardlink + sync + INDEX). |
| `airbyte-up` / `airbyte-tf-plan` / `airbyte-apply` recipes | not written | Lane implementation (writing-plans). |
| `abctl` runtime | not provisioned | Local, credential-gated; CI never applies. |
| CI can only `fmt`/`validate`/drift, not `plan` | by design (no reachable API without an instance) | Not a debt to fix — a documented limitation. Real `plan` lives on the opt-in local path. |
| STATUS persist (2026-07-23 turn) | skipped | Was DISK-CRITICAL (5Gi < 10Gi min). Re-run `/update-session-environment` after `/clean-disk`. |

## What IS done (not debt)

- `airbyte_emit.py validate` — real, green against the 591-connector live registry, negative-tested.
- Pre-commit gate `src/scripts/airbyte-blocks-check.sh` — fires on `spec/sources/` or the lane; self-skips off-machine.
- Settings, Justfile recipes, unit tests.
