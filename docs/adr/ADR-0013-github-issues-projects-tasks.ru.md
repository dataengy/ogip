<!-- ru-translation-of: docs/adr/ADR-0013-github-issues-projects-tasks.md sha:d499e8c4e268 -->
<!-- Автоперевод. Источник — docs/adr/ADR-0013-github-issues-projects-tasks.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0013-github-issues-projects-tasks.md](ADR-0013-github-issues-projects-tasks.md)

# ADR-0013 — GitHub Issues/Projects как трекер задач

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D12 · `.ai/TODO.md` · `.ai/tasks/` · `integrations/github/`

## Context

Портфолио-проекту полезен видимый, доступный для совместного использования трекер, тогда как
повседневная работа идёт в локальных файлах задач. Эти два уровня не должны расходиться.

## Decision

**GitHub Issues + доска GitHub Project** — единый трекер. Локальные `.ai/tasks/*` — рабочая
детализация, а `.ai/TODO.md` — короткий упорядоченный чек-лист; `just tasks-sync` проталкивает
задачи → Issues (идемпотентно по slug), добавляет их в Project и записывает номер issue обратно
(обратная ссылка). Токен через бэкенд секретов ([ADR-0011](ADR-0011-minimal-secrets.md)).

## Consequences

- Один разделяемый источник истины; локальные файлы остаются поверхностью для редактирования.
- Инструментарий синхронизации должен быть идемпотентным, чтобы не плодить дублирующие issue.

## Alternatives considered

- **Jira / Linear** — тяжелее, не видны в портфолио; Linear оставлен как опциональное личное зеркало.
- **Только локальные файлы задач** — не разделяемы; нет доски.
