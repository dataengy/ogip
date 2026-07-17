# ADR-0011 — Minimal secrets: `.env` + GitHub Actions secrets

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D10 · `docs/comparisons/secrets-management.md`

## Context

Secrets must stay out of git and work in CI. A vault + GPG combo was considered but is
over-built for a fork-and-run portfolio platform.

## Decision

Choose the **minimal, lightest** stack: secret slot *names* declared once in
`config/config.yml` (SSoT); a **gitignored `.env`** filled by hand for local + VPS; **GitHub
Actions encrypted secrets** for CI. No vault daemon, no GPG, no external account on the default
path. **Bitwarden CLI** and **git-secret** remain documented **opt-in** backends.

## Consequences

- Zero extra runtime dependency; trivial for a forker to run.
- No automated central rotation until an opt-in backend is enabled.

## Alternatives considered

- **Bitwarden + GitHub secrets + git-secret combo** — reverted: over-engineered for this scale.
