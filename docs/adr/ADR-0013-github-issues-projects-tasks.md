# ADR-0013 — GitHub Issues/Projects as the task tracker

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D12 · `.ai/TODO.md` · `.ai/tasks/` · `integrations/github/`

## Context

A portfolio project benefits from a visible, shareable tracker, while day-to-day work happens
in local task files. The two must not drift.

## Decision

**GitHub Issues + a GitHub Project board** are the single tracker. Local `.ai/tasks/*` are the
working detail and `.ai/TODO.md` the short ordered checklist; `just tasks-sync` pushes tasks →
Issues (idempotent by slug), adds them to the Project, and writes the issue number back
(backlink). Token via the secrets backend ([ADR-0011](ADR-0011-minimal-secrets.md)).

## Consequences

- One shareable source of truth; local files stay the editing surface.
- Sync tooling must be idempotent to avoid duplicate issues.

## Alternatives considered

- **Jira / Linear** — heavier, not portfolio-visible; Linear kept as an optional personal mirror.
- **Only local task files** — not shareable; no board.
