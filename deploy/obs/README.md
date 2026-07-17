# `deploy/obs/` — observability stack

VictoriaMetrics + Loki + Alloy + Grafana, wired for OGIP (Phase 7). Optional: the pipeline runs
green without it. Architecture, contracts and known gaps:
[`docs/architecture/observability.md`](../../docs/architecture/observability.md).

```bash
make obs-up          # start + verify   → Grafana http://localhost:3300
just obs-smoke-log   # prove the log path end-to-end (no pipeline run needed)
make obs-down        # stop (volumes preserved)
```

## Layout

```
deploy/obs/
├── docker-compose.obs.yml          # the stack (standalone — see below)
├── alloy/config.alloy              # tail logs → Loki; OTLP :4317/:4318 → VictoriaMetrics
├── victoriametrics/scrape.yml      # scrape the stack's own health (NOT the pipeline)
└── grafana/
    ├── provisioning/               # datasources + dashboard provider (no click-ops)
    └── dashboards/*.json           # dashboards as code
```

## Why a standalone compose file

`make obs-up` does **not** use `deploy/docker-compose.yml --profile obs`, even though the
Makefile once did: that base file (Postgres, Prefect, MinIO) is owned by other work lanes and
does not exist yet. A standalone file keeps this stack shippable on its own and conflict-free
across parallel sessions ([`.ai/STATUS.md`](../../.ai/STATUS.md) → lane `obs`).

When the base compose lands, merge by swapping the `ogip-obs` network for
`networks: {ogip: {external: true}}` — no service definitions need to change.

## Conventions

- **Ports** come from `config/config.yml` (SSoT) via the rendered `.env`; the `${VAR:-default}`
  fallbacks mirror the SSoT so a bare checkout still boots. See "Ports & the SSoT gap" in the
  architecture doc.
- **Healthchecks everywhere except Alloy**: VM/Loki/Grafana self-probe with the busybox `wget`
  their images carry. `grafana/alloy` ships no HTTP client at all (no wget/curl/nc), so a
  healthcheck there would point at a missing binary and sit unhealthy forever — hanging
  `up --wait`. [`src/scripts/obs-verify.sh`](../../src/scripts/obs-verify.sh) covers Alloy and
  checks every published port from the host.
- **VM healthcheck uses `127.0.0.1`, not `localhost`**: VictoriaMetrics binds IPv4 only, and
  busybox `wget` resolves `localhost` to `::1` first → connection refused.
- **Dashboards are code**: UI edits are disabled (`allowUiUpdates: false`). Change the JSON,
  re-run `make obs-up`.
- **Images are pinned** — bump deliberately, never by `:latest` drift.
