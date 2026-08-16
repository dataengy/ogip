# Task — cloud-devops readiness ([#53](https://github.com/dataengy/ogip/issues/53))

> 🇷🇺 Русская версия: [cloud-devops-readiness.ru.md](cloud-devops-readiness.ru.md)

**Role:** [`.claude/agents/ogip-cloud-devops.md`](../../.claude/agents/ogip-cloud-devops.md) ·
**Matrix:** [`config/verify.yml`](../../config/verify.yml) ·
**Lane:** `cloud-devops` (this file, the agent file, the matrix; `deploy/vps/` stays with
`core-pipeline` / [#17](https://github.com/dataengy/ogip/issues/17))

Prove OGIP works **fully locally**, prove it can be **fully deployed + run + verified off the
workstation** (manual VPS, [ADR-0012](../../docs/adr/ADR-0012-github-ci-manual-vps-deploy.md)),
upsert what that requires, and keep a current **deploy proposal** in front of the owner —
deploys themselves are human-approved, always.

## How to run

```bash
JF=~/.ai/skills/_scripts/infra/project-readiness/Justfile   # skills-catalog runner
just -f "$JF" verify local    # whole-project local verification (CI-parity stages)
just -f "$JF" verify cloud    # deployability: assets, runbooks, CI, escrow, vps dry-runs
```

Skill family (catalog `infra/project-readiness`): `/verify-project-local-full` →
`/verify-project-cloud-deployable` → `/propose-project-deploy` (slash-only, human gate).

## Status

- [x] Verification matrix (`config/verify.yml`) — local (8 stages) + cloud (8 stages)
- [x] Skill family created in the catalog + stage runner (`verify-stages.sh`)
- [x] Role agent `ogip-cloud-devops`
- [x] Skills approved at the review gate → deployed to `~/.claude/skills` + synced to
      other agent targets (2026-08-16, hardlinks verified by inode; provenance stamped)
- [x] First full readiness run recorded below
- [ ] Deploy proposal approved / rejected by owner

## Readiness log

| date | local verdict | cloud verdict | notes |
|---|---|---|---|
| 2026-08-16 | **LOCAL-VERIFIED** (6 PASS · 2 WARN) | **DEPLOYABLE-WITH-OPERATOR-INPUT** (5 PASS · 3 NEEDS-OPERATOR) | e2e ran the Prefect job, 10/10 DQ monitors green, artifacts in `.run/data/outputs/`; CI green on `dev`. WARNs: obs-stack (docker daemon down on this host), structure-validate (see handoff). Operator inputs: `OGIP_VPS_HOST` + secrets escrow. |

## Findings / handoffs

1. **Handoff → lane `core-pipeline`** (`.ci/` owner): `.ci/steps/structure-validate.sh`
   counts **gitignored** files, so sanctioned local `*.ru.md` translations (`AGENTS.ru.md`,
   `README.ru.md`) fail it locally while CI's clean checkout passes. Fix: enumerate via
   `git ls-files --others --exclude-standard` (+tracked) instead of raw `ls`. Until then the
   matrix carries the stage as `optional`.
2. **Secrets escrow not performed** (human steps, [#52](https://github.com/dataengy/ogip/issues/52)):
   `just secrets-doctor` reports backends healthy but git-secret `initialized=NO`, no
   `.env.secrets.secret` blob. Required slots for a deploy: `OGIP_PG_PASSWORD`,
   `RAWG_API_KEY` (`deploy/vps/check-secrets.sh`). Escrow before any VPS deploy:
   `just secrets-setup-git-secret && just secrets-hide` (needs GPG key) **or** `bw unlock` +
   `just secrets-push`.
3. **dev CI e2e red — Bruin CLI drift** ([#54](https://github.com/dataengy/ogip/issues/54),
   handoff → `core-pipeline`): CI installs unpinned latest Bruin; the `[bruin]` e2e case fails
   there while local v0.11.680 is green. Blocks dev→main promotion (not the `main` deploy —
   `main` CI is green). Fix: pin the CLI version in `.github/workflows/ci.yml`. Until then the
   `ci-green-dev` cloud stage fails honestly.
