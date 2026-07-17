# Task — Unified alerting: Notifier + Telegram/Mattermost/Slack (Phase 7)

**Status:** 🚧 in progress — abstraction + three transports shipped, unit-tested and verified
against the live Telegram API. Config still env-driven (SSoT section is a handoff); no alert
source is wired yet.

Lane: `alerting` (parallel-session lock object). Scope: `src/ogip/alerting/`,
`src/tests/unit/test_alerting.py`. Issue: [#11](https://github.com/dataengy/ogip/issues/11).
Part of **Phase 7 — Observability** ([PLAN](../PLAN.md) A10) alongside the obs stack
([observability.md](../../docs/architecture/observability.md)).

## Why

PLAN A10 calls for a `Notifier` Protocol — an alerts abstraction, so business code says *what*
happened and never learns *where* it goes. The obs stack (VictoriaMetrics/Loki/Grafana) answers
"what is happening"; alerting answers "someone needs to know now".

## Delivered

- `base.py` — `Messenger` protocol (how to deliver), `Notifier` (whether/what: dry-run,
  fallback, **never raises**), `NotifyResult`, `split_message`.
- `telegram.py` · `mattermost.py` · `slack.py` — three transports, each with a health check.
- `settings.py` — `OGIP_ALERT_*` routing + `OGIP_TG_*` / `OGIP_MM_*` / `OGIP_SLACK_*` creds.
- `__init__.py` — `make_notifier()`; returns `None` when nothing is configured, so a
  credential-free pipeline stays green and simply stays quiet.
- 23 unit tests (respx-mocked httpx), mutation-checked.

## Design notes

- **An alert must not become a second failure.** `notify()` returns a result, never raises.
- **A fallback delivery is still a degradation.** It reports `sent=True` with the *fallback's*
  name and a reason naming the primary that failed — the alert survives, the problem stays visible.
- **No retries.** A failing primary falls straight to the fallback rather than parking an
  already-unhappy pipeline behind backoff.
- **The Slack trap**: `chat.postMessage` answers `HTTP 200` with `{"ok": false}` on failure.
  Status-code-only handling would silently swallow every such alert, so `ok` is checked and raised on.
- Architecture adapted from a mature private monitoring stack; code is clean-room — no
  corporate ticket ids, hostnames or bot names in this public repo.

## Verified

- `ruff` · `pyright --strict` · 23/23 pytest green.
- **Live Telegram** (not mocks): `getMe` health check, a real delivery, a 5464-char message
  split and delivered in 2 posts, and a deliberately-broken primary degrading onto the fallback.
- Mutation-checked: removing the Slack `ok` guard or the split limit turns the suite red.

## Blocked on / handoff

→ lane `core-pipeline` (owns `config/`): move routing into `config/config.yml` `alerting:` +
map it in `config/.env-render.py` (incl. secret slots), then swap the literal defaults in
`settings.py` for `_yaml("alerting", …)`. Detail: [STATUS.md](../STATUS.md).

Deferred until the parallel lanes finish:

- Flow-failure alerts wired into `pipelines/` (lane `core-pipeline`).
- Grafana/VM alert rules → webhook receiver → `Notifier` (lane `obs`).
