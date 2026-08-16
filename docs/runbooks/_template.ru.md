<!-- ru-translation-of: docs/runbooks/_template.md sha:e14335f7857a -->
<!-- Автоперевод. Источник — docs/runbooks/_template.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [_template.md](_template.md)

# Runbook — <title>

- **Trigger:** какая ситуация или запрос запускает эту процедуру.
- **Owner:** ответственная роль. **Severity/urgency:** если связано с инцидентом.

## Preconditions

- Доступ, инструменты, окружение (`.env` отрендерен, доступны секреты `bw`/GitHub), ожидаемые поднятые сервисы.

## Steps

1. Конкретные, готовые к копированию команды (`make …` / `just …` / `gh …`).
2. …

## Verify

- Как подтвердить успех (ожидаемый вывод, зелёный запуск Prefect, число строк, наличие файла).

## Rollback

- Как безопасно откатить, если шаг провалился.

## Escalation

- К кому/чему обращаться при блокировке (примечание: infra/DevOps обрабатывается отдельно).
