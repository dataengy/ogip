# Task — Agentic observability: monitor the agents building OGIP (standard-first)

**Status:** 🚧 in progress — plan approved 2026-07-19; Phase 0 (OTel spike) underway.

Lane: `obs`. Scope: `deploy/obs/**`, `src/scripts/obs-*`, `.claude/settings.local.json`
(opt-in telemetry), docs. Plan: `~/.claude/plans/fable-xhigh-silly-melody.md` (session-local).

## Why

The obs stack watches the pipeline; nobody watches the **agents** building it — several
parallel Claude Code sessions burn tokens, run skills/subagents, hold lanes and ship commits
with zero dashboards, zero trend alerting. Skill-catalog audit confirmed the gaps: no
token/cost analytics, no subagent analytics, no trend alerts, no GitHub-work dashboards, no
Grafana surface for any of it.

**Standing directive: standard specialized tools over self-built toolkit.**

## Approach (what standard tool answers each ask)

| Ask | Standard tool |
|---|---|
| Alerting on agent activity | Claude Code **native OTel** → Alloy (:4318, already live) → VM/Loki → **Grafana unified alerting** (provisioned as code) → **native Telegram contact point** |
| Session status/progress dashboards | Grafana on `claude_code_*` metrics + OTLP events in Loki |
| Token/skills/subagents efficiency | OTel metrics (live) + **ccusage via npx** (history); skills already covered by `session-skills-digest.py` |
| Overall agentic health | same Grafana dashboard (`ogip-agentic.json`); Evidence/Metabase deliberately NOT used |
| GitHub issues/projects work | **GitHub Projects v2 + Insights**, zero code; `tasks_sync.py` unchanged |

## Phases

0. **OTel spike** (gates all): env-prefixed session → exact `claude_code_*` series names in VM;
   event attributes; exporter noise when stack down. Fallback: ccusage-only, no custom collector.
1. Alloy: route OTLP **logs** → Loki (labels: `service.name` + `event.name` only).
2. Grafana alerting provisioning (contact-points/policies/5 rules) + **dedicated TG chat**
   (interactive onboarding, creds via existing add-secret flow; `$VAR` interpolation — no
   secrets in YAML). Repurposes the webhook-receiver idea from the obs-alerting-tail task:
   Grafana-native delivery replaces the custom receiver; the in-process `Notifier` stays for
   Prefect hooks.
3. `ogip-agentic.json` dashboard (sessions/progress · efficiency incl. `Agent|Skill` tool
   table · health).
4. Enablement: `.claude/settings.local.json` env block (promotion to shared settings via the
   session-coordination task), `just agentic-usage` (ccusage), docs, glossary upsert.
5. GitHub Projects v2 + Insights (needs `gh auth refresh -s project,read:project`).
6. Bookkeeping. Flow-hook regression after the engines/ refactor: ✅ verified — the hook moved
   into the shared flow factory (`pipelines/flows/_common.py`), all engine flows carry it.

## Explicitly not built

Custom webhook receiver · custom JSONL collectors/parsers · Evidence/Metabase · new
notification skills. Each is covered by a standard tool above.
