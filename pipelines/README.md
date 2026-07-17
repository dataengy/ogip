# `pipelines/`

**Prefect 3** flows and deployments (ADR-0007). The production driver composes
`ingest → transform → dq → publish_outputs`; idempotent and parameterized.

| Subdir | Holds |
|---|---|
| `flows/` | Prefect flows (the daily driver + per-stage flows) |
| `deployments/` | Prefect deployment definitions (`integrations/prefect/` deploys/triggers them) |

_Built from Phase 6; M0 wires the minimal end-to-end flow._
