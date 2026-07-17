# Task — `spec/`: engine-agnostic semantic layer description (Bruin Semantic Layer)

**Status:** 📋 planned · **Priority:** mid

Lane: `spec`. Scope: `spec/`. Issue: — (create via `just tasks-sync`).
Part of the `spec/` SSoT track ([PLAN](../PLAN.md) A2 · A4): semantic *frameworks* stay in
`experimental/semantic/` (MetricFlow/Cube demos) and consume `spec/`, so the semantic
*definitions* themselves belong in the agnostic spec layer.

## Goal

Describe OGIP's semantic layer — entities, dimensions, measures/metrics over the
CORE/STAR/AM/MARTS models — **engine-agnostically inside `spec/`**, authored in the
[Bruin Semantic Layer](https://getbruin.com/docs/bruin/core-concepts/semantic-layer.html#semantic-layer)
format. Consistent with D0: spec authored in Bruin's open serialization; Bruin stays an
authoring format, not a prod dependency.

## Sketch

- [ ] Study the Bruin Semantic Layer format (docs link above) — verify exact syntax at
      authoring time, per the A2 note.
- [ ] Add `spec/semantic/` (or extend the Bruin asset metadata) describing entities ·
      dimensions · measures for the M0 slice models first.
- [ ] Keep it consumable by `experimental/semantic/` (MetricFlow/Cube demos, Phase 9) and
      the spec compiler; no production-path dependency.
- [ ] Document in the `spec/` README + link from PLAN A2 when landed.

## Acceptance

- Semantic definitions live in `spec/` as data (Bruin semantic-layer YAML), readable
  without any engine binary.
- `experimental/semantic/` demos (when built) consume them instead of redefining metrics.
