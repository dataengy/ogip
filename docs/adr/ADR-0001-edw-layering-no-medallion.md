# ADR-0001 — Classical EDW layering, no medallion vocabulary

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** ARCHITECTURE · layer naming law

## Context

Layers need testable contracts, not quality-tier labels. "Bronze/silver/gold" names a
tier but says nothing about modeling contracts or ownership.

## Decision

Use classical EDW layers, each with a hard contract and a naming law:
`0 raw <system>__<table>` → `1 stg_*` → `2 core` (3NF + partial DV) → `3 *_fact/*_dim` (Kimball
star) → `4 am_<entity>_stream` (Activity Schema) → `5 owt_*/agg_*` (marts) → `6 fs_*` (feature
store). Skipping layers downward is forbidden. **No medallion vocabulary anywhere.**

## Consequences

- Each layer stays simple, independently testable, and owned.
- Contributors must respect the naming law (enforced by a structure guard in CI).

## Alternatives considered

- **Medallion (bronze/silver/gold)** — rejected: encodes quality tiers, not modeling contracts.
