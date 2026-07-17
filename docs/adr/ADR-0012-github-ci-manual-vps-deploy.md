# ADR-0012 — GitHub Actions CI + manual VPS deploy (DevOps separate)

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D9 · `deploy/vps/` · `docs/runbooks/deploy-vps.md`

## Context

The project needs a gate on every change and a deployment story, but infrastructure/DevOps is
handled separately and is out of scope for this repo.

## Decision

**CI = GitHub Actions**: type-check (Pyright strict) + test suite (pytest) + pre-commit, over a
shared `.ci/steps/` library. **Deployment = manual on a VPS** via `deploy/vps/` (uv sync, render
env, secrets, prefect deploy, compose up), documented as a runbook. No Kubernetes/Terraform.

## Consequences

- Byte-stable CI logic; warehouse-in-CI is cheap on DuckDB.
- Deploy is manual and runbook-driven; automation is explicitly out of scope (DevOps separate).

## Alternatives considered

- **GitLab CI dual-frontend** (OGAP) — kept optional; GitHub Actions is the only required CI.
- **k8s/Terraform** — over-scoped; DevOps owns infra separately.
