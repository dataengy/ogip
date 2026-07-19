# OGIP — AI glossary (EN)

Terms that keep resurfacing in agent sessions on this repo — infra, tooling, and the
project's own coordination vocabulary. Written by `/update-terms-glossaries` (the writer
behind `/add-terms-to-glossary`); Russian-slang twins live in
[AI-glossary.ru.md](AI-glossary.ru.md).

## Quick index

| Term | Marker | Short |
|---|---|---|
| [OTel / OTLP (Claude Code native telemetry)](#otel--otlp-claude-code-native-telemetry) | general | агентские метрики/события из Claude Code по стандартному OTLP — без кастомных коллекторов |
| [delta vs cumulative temporality](#delta-vs-cumulative-temporality) | general | OTel-метрики бывают delta/cumulative; prometheus-экспортеры МОЛЧА дропают delta |
| [Grafana alerting-as-code (unified alerting provisioning)](#grafana-alerting-as-code-unified-alerting-provisioning) | general | contact points + policies + rules как YAML в provisioning/alerting/ — алертинг в git |
| [ccusage](#ccusage) | general | npx ccusage — OSS-отчёты токенов/стоимости из ~/.claude/projects/*.jsonl |
| [label cardinality guard](#label-cardinality-guard) | general | в лейблы попадают только низкокардинальные поля; id-шники живут в строке |
| [lane locks / lane-status.sh / release-all-mine](#lane-locks--lane-statussh--release-all-mine) | project | координация параллельных агент-сессий OGIP: пер-полосные advisory-локи + снапшот + sweep на выходе |

## OTel / OTLP (Claude Code native telemetry)

`[general]` Claude Code's built-in OpenTelemetry export (env-gated: CLAUDE_CODE_ENABLE_TELEMETRY=1 + OTEL_METRICS_EXPORTER/OTEL_LOGS_EXPORTER=otlp) — pushes token/cost/session metrics and user_prompt/api_request/tool_result events over OTLP to any collector endpoint.
> **RU:** Встроенный OTel-экспорт Claude Code: метрики (токены/стоимость/сессии) и события агентской сессии уходят по OTLP в коллектор (Alloy :4318) — дашборды по агентам без единой строчки самописного парсинга.
> **Пример:** OGIP #33: env-блок в .claude/settings.local.json → Alloy → VictoriaMetrics/Loki → дашборд «OGIP — Agentic Activity».

## delta vs cumulative temporality

`[general]` OTel metric temporality: delta reports change-since-last-export, cumulative reports running totals. Prometheus-style exporters (incl. Alloy's otelcol.exporter.prometheus) silently drop delta series — no error anywhere.
> **RU:** Темпоральность OTel-метрик. Claude Code по умолчанию шлёт delta → в VictoriaMetrics не долетает НИЧЕГО и нигде нет ошибки. Лечится клиентски: OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=cumulative — обязательная строка env-блока.
> **Пример:** OGIP spike 2026-07-19: receiver принял 7 точек, VM пуст; после cumulative — все 4 серии claude_code_* на месте.

## Grafana alerting-as-code (unified alerting provisioning)

`[general]` Grafana's file-provisioned unified alerting: contact-points.yml, policies.yml, rules.yml under provisioning/alerting/ — the whole alert pipeline lives in the repo, UI edits disabled.
> **RU:** Алертинг Grafana целиком кодом: контакт-поинты, роутинг и правила — YAML в репо. Нативный Telegram contact point заменяет самописные webhook-приёмники. Грабля: env-интерполяция пере-инферит тип значения — числовой chatid спасает хвостовой пробел в шаблоне.
> **Пример:** OGIP deploy/obs/grafana/provisioning/alerting/ — 4 правила, доставка в @test_cha_2 проверена receivers-test API (status=ok).

## ccusage

`[general]` OSS CLI (npx ccusage@latest daily|session|blocks) that reads local agent transcripts (~/.claude/projects/**.jsonl) and prints token/cost tables per day/session/model — the standard offline usage reporter, no telemetry needed.
> **RU:** Стандартный офлайн-репортёр расхода токенов/денег по локальным транскриптам агентов; исторический срез там, где Grafana даёт live.
> **Пример:** OGIP: just agentic-usage --since 20260716 — таблица по дням, видны Claude и Codex.

## label cardinality guard

`[general]` The rule that only low-cardinality fields (service.name, event.name, level) may become Loki/Prometheus labels; per-run/per-session ids stay in the log line — a per-id label multiplies streams and takes the store down.
> **RU:** Правило: session_id/flow_run_id — НЕ лейблы. В OGIP закреплено дважды: flow_run в файловом пайплайне и session.id в OTLP-пути Alloy.
> **Пример:** config.alloy §3: hint-атрибуты промоутят только service.name + event.name.

## lane locks / lane-status.sh / release-all-mine

`[project]` OGIP's parallel-session discipline: advisory per-lane object locks (.ai/.locks/obj--<lane>), lane-status.sh (one-shot locks/git/settle snapshot with --wait), and the release-all-mine verb the SessionEnd hook runs so a dying session frees every lane it held.
> **RU:** Дисциплина полос OGIP: claim перед записью, снапшот перед claim'ом, автоматический sweep всех своих локов на SessionEnd.
> **Пример:** bash src/scripts/lane-status.sh → VERDICT: GO/COORDINATE; хук зовёт agent-session-lock.sh release-all-mine.
