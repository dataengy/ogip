# HANDOFF / compact snapshot — cloud-devops readiness (2026-08-20)

Session scope: [#53](https://github.com/dataengy/ogip/issues/53) — cloud-devops role, verify
skills, readiness audit, deploy proposal.

## Open tasks with keys

- [#53](https://github.com/dataengy/ogip/issues/53) — cloud-devops readiness: **deliverables
  shipped**; stays open until the deploy proposal is decided and the first deploy is logged
  in [tasks/cloud-devops-readiness.md](../tasks/cloud-devops-readiness.md) readiness log.
- [#54](https://github.com/dataengy/ogip/issues/54) — dev CI e2e red (`[bruin]` case) under
  CI's unpinned latest Bruin CLI. **Handoff to lane `core-pipeline`** (owns `.ci/` +
  workflows): pin the version in `.github/workflows/ci.yml`. dev→main promotion blocked
  until fixed.
- [#52](https://github.com/dataengy/ogip/issues/52) — secrets escrow human steps still
  pending: git-secret `initialized=NO`, no blob; slots `OGIP_PG_PASSWORD`, `RAWG_API_KEY`.

## Done, with commit SHAs (all on `dev`, pushed)

- `85ca791` feat(config): `config/verify.yml` — 16-stage local+cloud verification matrix.
- `bc4cf5c` chore(ai): `.claude/agents/ogip-cloud-devops.md` (role agent, registered),
  `.ai/tasks/cloud-devops-readiness.md`, `.ai/SKILLS.md` in-use rows.
- `d3fce67` chore(ai): #54 finding recorded.
- `a3c3e39` chore(ai): skills review-gate approval recorded.
- Skills catalog (`~/.ai/skills/_catalog/infra/project-readiness/`):
  `verify-project-local-full` · `verify-project-cloud-deployable` ·
  `propose-project-deploy` (slash-only) + runner
  `~/.ai/skills/_scripts/infra/project-readiness/{verify-stages.sh,Justfile}`.
  **Approved 2026-08-16 and deployed**: hardlinked into `~/.claude/skills` (inode-verified),
  provenance-stamped, synced claude→codex, INDEX rows appended.
- First readiness run (2026-08-16): **LOCAL-VERIFIED** (e2e Prefect run, 10/10 DQ monitors,
  artifacts `.run/data/outputs/*.parquet`) · **DEPLOYABLE-WITH-OPERATOR-INPUT**
  (host + escrow are the only blockers). Result comment: #53.

## Unresolved, with reason

- **Deploy proposal awaiting owner decision** — main → Hetzner-class VPS per ADR-0012;
  agent may not deploy without explicit approval. Steps live in
  [tasks/cloud-devops-readiness.md](../tasks/cloud-devops-readiness.md) + #53 comment.
- **Skills-repo commit**: the catalog/runner/INDEX additions are on disk but UNCOMMITTED in
  `~/.ai/skills` (that repo is owner-driven and was already 1244 files dirty — committing
  would sweep foreign work). Risk: `git clean` there would destroy them.
- **structure-validate handoff** (in #53 task file): `.ci/steps/structure-validate.sh`
  counts gitignored files; stage is `optional: true` in the matrix until core-pipeline fixes
  it.
- Pre-existing docs-check hook flag "1 doc missing/stale RU" — predates this session, not
  triaged here.

## Decisions accepted (do not re-litigate)

- Skill family lives in catalog domain `infra/project-readiness`; classifier tier =
  default/normal (not heavy).
- `propose-project-deploy` is slash-only (`disable-model-invocation: true`); deploys are
  always human-gated (ADR-0012).
- e2e evidence paths use `platform.data_dir` (`.run/data/outputs/`), NOT `outputs/`.
- CI-parity principle: matrix stages mirror `.ci/steps/*`; blank `OGIP_VPS_HOST` ⇒
  NEEDS-OPERATOR, by design.
- Lane `cloud-devops` = `config/verify.yml` + agent file + task file; `deploy/vps/` stays
  with `core-pipeline` (#17).

## Resume

```bash
just -f ~/.ai/skills/_scripts/infra/project-readiness/Justfile verify local   # re-baseline
just -f ~/.ai/skills/_scripts/infra/project-readiness/Justfile verify cloud
```
