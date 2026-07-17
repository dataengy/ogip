# ADR-0010 — Activity Model (Activity Schema) layer

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D13 · [ADR-0001](ADR-0001-edw-layering-no-medallion.md) · `docs/comparisons/modeling-techniques.md`

## Context

Kimball star and partial Data Vault model entities and facts well, but time-series "what did
this entity do" questions (release, price change, review, stream, mention) are awkward across
many facts. The [Activity Schema](https://www.activityschema.com/) models all of it as one
time-series stream.

## Decision

Add an **Activity Model (AM)** layer (Layer 4): `am_<entity>_stream` — a single Activity-Schema
activity stream per entity (one row per activity: `entity_id`, `ts`, `activity`, features,
`activity_occurrence`, `activity_repeated_at`), built from CORE. It complements the Kimball STAR
(both over CORE) and feeds MARTS/FS. Datasets derive via temporal joins (first/last/aggregate).

## Consequences

- Four modeling techniques showcased: 3NF · partial Data Vault · Kimball · Activity Schema.
- One more analytical layer to maintain; kept SQL-only (SQLMesh), no new tooling.

## Alternatives considered

- **Kimball only** — misses the unified activity-stream technique this project wants to demonstrate.
