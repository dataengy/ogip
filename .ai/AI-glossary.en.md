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
| [:= vs = в проекции (PropertyEQ vs EQ)](#=-vs-=-в-проекции-propertyeq-vs-eq) | general | `a = b` в проекции — предикат равенства, boolean-колонка: валидно, исполняемо, молча не то; `a := b` падает громко |
| [macro conformance test](#macro-conformance-test) | general | один макрос × все адаптеры × одна фикстура, assert байт-в-байт — защита от тихого расхождения реализаций |
| [ODPS / ODTS / ODOS (семейство стандартов)](#odps--odts--odos-семейство-стандартов) | project | зонт называется YADPS, а не ODPS — имя занято Bitol и LF; конвенция: конфликтующее имя берёт YA вместо Open |
| [@odts](#@odts) | project | формат авторинга spec/sql в OGIP: компактный header → рендер в @bruin YAML → адаптеры без изменений |
| [.ai/FIXME.md (conflict register)](#aifixmemd-conflict-register) | project | реестр известных противоречий между документами; протухшее hard rule опаснее протухшего README |

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

## := vs = в проекции (PropertyEQ vs EQ)

`[general]` In sqlglot, `select a = b` parses as `EQ` — an equality predicate yielding a boolean column — while `select a := b` parses as `PropertyEQ`. Only the second is unambiguous, and DuckDB rejects it outright instead of running it.
> **RU:** `a = b` в проекции — валидный, исполняемый и молча неверный SQL: на выходе boolean-колонка вместо алиаса. `a := b` даёт отдельный узел AST и падает громко, поэтому безопасен как авторский сахар.
> **Пример:** OGIP ADR-0016: LValue разрешён только через `:=`, `=` запрещён наглухо — проверено на sqlglot 30.8 / DuckDB 1.5.4.

## macro conformance test

`[general]` When one macro compiles to several engine-native implementations, a test that runs every adapter over one fixture and asserts byte-identical output.
> **RU:** Когда один макрос компилируется в несколько нативных реализаций — тест, гоняющий все адаптеры по одной фикстуре с assert байт-в-байт. Без него `dbt_utils.generate_surrogate_key` и `md5(cast(x as varchar))` дают разные хеши, и модель keyится по-разному в зависимости от run-профиля.
> **Пример:** OGIP #36: условие приземления макроса, а не пожелание — расхождение делает CI красным, а не инцидентом данных ниже по потоку.

## ODPS / ODTS / ODOS (семейство стандартов)

`[project]` The project's standards taxonomy: **YADPS** (Yet Another Data Platform Standard) as the umbrella, with **ODTS** (Open Data Transformation Standard) and **ODOS** (Open Data Orchestration Standard) as parts. The umbrella is *not* called ODPS: that acronym is held by Bitol's Open Data Product Standard and the Linux Foundation's Open Data Product Specification, and Bitol also maintains ODCS which `spec/contracts/` already uses. **Convention — a colliding name takes `YA` (Yet Another) in place of `Open`.** ODTS and ODOS were checked and are unclaimed, so they keep `Open`; the family is deliberately asymmetric.
> **RU:** Таксономия стандартов проекта: **YADPS** (Yet Another Data Platform Standard) — зонт, **ODTS** (трансформации) и **ODOS** (оркестрация) — части. Зонт называется НЕ ODPS: это имя занято Open Data Product Standard от Bitol и Open Data Product Specification от Linux Foundation, а Bitol же ведёт ODCS, который уже используется в `spec/contracts/`. **Конвенция: конфликтующее имя берёт `YA` вместо `Open`.** ODTS и ODOS проверены и свободны — поэтому сохраняют `Open`; асимметрия семейства намеренная, маркер несёт только то имя, что наступило на занятое.
> **Пример:** Разделение ODTS/ODOS подтверждает архитектурный выбор OGIP: оркестраторы (Prefect, Dagster) — не таргеты компиляции ODTS, у них своя ось и свой стандарт.

## @odts

`[project]` OGIP's authoring format for `spec/sql` and its implementation of ODTS — a compact line-oriented header compiled front-of-pipeline into the legacy `@bruin` YAML, so the compiler is extended at the front and every adapter stays untouched.
> **RU:** Формат авторинга `spec/sql` в OGIP и его реализация ODTS. Компактный header компилируется фронтендом в `@bruin` YAML, поэтому компилятор расширяется спереди, а адаптеры не трогаются вообще. OGIP реализует стандарт, а не авторствует его: рамка оценки — шесть реальных таргетов проекта.
> **Пример:** ADR-0016; задачи #35 (компактный header) и #36 (макро-слой).

## .ai/FIXME.md (conflict register)

`[project]` OGIP's register of known contradictions between documents and convention gaps — sits between `TODO.md` (near-term actions) and `tasks/` (scoped work with an issue). It exists because the project asserts facts in prose rather than deriving them: the `spec/sql` authoring format alone is stated in ten documents.
> **RU:** Реестр известных противоречий между документами и пробелов в конвенциях — между `TODO.md` и `tasks/`. Нужен потому, что факты в проекте заявляются прозой, а не выводятся: один только формат авторинга `spec/sql` записан в десяти документах. Ключевое правило: протухшее hard rule в `AGENTS.md` опаснее протухшего README — hard rules **исполняют**, а не просто читают.
> **Пример:** F1: hard rule 2 всё ещё говорит «Bruin asset format» и станет ложью в момент приземления #35.
