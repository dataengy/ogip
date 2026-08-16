# Techdebt — Airbyte evaluation lane

> 🇷🇺 Русская версия: [airbyte-lane.ru.md](airbyte-lane.ru.md)

One row per deferred item, each with the condition that unblocks it. Pattern rationale:
`~/.ai/skills/.settings/code_specs/script_standards.yml#deferred_functionality` — mark loudly,
never fake. Design SSoT: `docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md`.

| Item | State | Unblock condition |
|---|---|---|
| `airbyte_emit.py render <a\|b\|c>` | loud stub, exits 2 | Superseded — the `airbyte-connection` module now exists (Phase 2). Variant B/C renderers become the work; see Phase 4. |
| **Phase 1 abctl runtime — NO-GO on this machine (2026-07-25)** | **attempted, failed** | See the "Phase 1 result" note below. Re-attempt needs ≥20Gi free + an unthrottled network, OR a remote/CI-hosted Airbyte. Blocks Phase 3 (`plan`/`apply` datapoint) and Phase 5 (twitch sync). |
| Trapped colima disk (~10Gi) | the failed install inflated colima's diffdisk; freed inside the VM but not returned to the host | Needs `colima stop` → compact/`colima delete` → restart. **Blocked**: another live session's OGIP obs stack (grafana/alloy/loki/vm) runs inside the same colima — coordinate before reclaiming. |
| Skill `/add-airbyte-sync` deploy | at review gate — agents-hub symlink only; NOT hardlinked to `~/.claude/skills`, not synced | The lane's `apply`/`render` are real (needs a working runtime); then finish `/create-skill` steps 13-15. |
| `airbyte-tf-plan` / `airbyte-apply` recipes | not written | A working runtime (Phase 1) + Phase 3 variant-a. `airbyte-up`/`-down`/`-creds` + `airbyte-validate` ARE written. |
| CI can only `fmt`/`validate`/drift, not `plan` | by design (no reachable API without an instance) | Not a debt to fix — a documented limitation. Real `plan` lives on the opt-in local path. |
| STATUS persist | pending | Re-run `/update-session-environment` once disk clears (currently ~3Gi, colima-trapped). |

## Phase 1 result — abctl NO-GO on this machine (2026-07-25)

This is the plan's hard go/no-go gate, and it went **no-go** — a real finding, not a code defect.
`abctl v0.30.4` + colima/Docker 29.5.2 got as far as **creating the kind cluster and pulling
the ~14 Airbyte images (~5GB, 29 min under corp-VPN throttling)**, then failed at the Helm step:

```
ERROR  Failed to install airbyte/airbyte Helm Chart
ERROR  Kubernetes cluster unreachable: Get "https://127.0.0.1:63702/version": net/http: TLS handshake timeout
```

Root cause = **disk exhaustion during image extraction**, not an abctl/provider incompatibility
(Helm never deployed, so the provider was never exercised against a live API). Image pull drove
free space from ~13Gi to 2Gi; a disk-guard killed the install at the 3Gi floor to protect the
repo (which stayed intact). The provider-side premise is therefore **still unverified** — the
runtime never came up. `up.sh`'s gate was raised 10→20Gi to reflect the measured peak.

**What this means for the evaluation:** on a constrained, VPN-throttled workstation that already
hosts the obs stack in colima, the abctl runtime is impractical. A fair Airbyte evaluation needs
either a machine with ≥20Gi headroom and open egress, or a remote/hosted Airbyte the provider can
reach. The offline-verifiable parts of the lane (module `validate`, CI `fmt`/`validate`, block
validation) do NOT need the runtime and are done/doable; the *measured* sync datapoints (Phase 3
`apply`, Phase 5 twitch) are blocked until a runtime exists.

## What IS done (not debt)

- `airbyte_emit.py validate` — real, green against the 591-connector live registry, negative-tested.
- Pre-commit gate `src/scripts/airbyte-blocks-check.sh` — fires on `spec/sources/` or the lane; self-skips off-machine.
- Shared Terraform module `airbyte-connection` — schema-verified against provider 1.2.0, `init`+`validate` green (Phase 2).
- Runtime scripts `up.sh`/`down.sh`/`credentials.sh` + Justfile passthroughs `airbyte-up`/`-down`/`-creds`/`-validate` (Phase 1 scripts; the *runtime they drive* is the no-go above).
- Settings, Justfile recipes, unit tests.
