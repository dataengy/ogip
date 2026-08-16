<!-- ru-translation-of: docs/techdebt/airbyte-lane.md sha:d90122b5efca -->
<!-- Автоперевод. Источник — docs/techdebt/airbyte-lane.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [airbyte-lane.md](airbyte-lane.md)

# Техдолг — оценочная ветка Airbyte

Одна строка на каждый отложенный пункт, у каждого — условие, которое его разблокирует.
Обоснование паттерна:
`~/.ai/skills/.settings/code_specs/script_standards.yml#deferred_functionality` — помечай
громко, никогда не фальсифицируй. SSoT дизайна:
`docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md`.

| Пункт | Состояние | Условие разблокировки |
|---|---|---|
| `airbyte_emit.py render <a\|b\|c>` | громкая заглушка, выходит с кодом 2 | Существует модуль `experimental/ingestion/airbyte/terraform/modules/airbyte-connection`. |
| Деплой скилла `/add-airbyte-sync` | на ревью-гейте — только symlink в agents-hub; НЕ захардлинкован в `~/.claude/skills`, не синхронизирован в остальные цели | Ветка построена, а `apply`/`render` реальны; затем завершить шаги 13-15 `/create-skill` (hardlink + sync + INDEX). |
| Рецепты `airbyte-up` / `airbyte-tf-plan` / `airbyte-apply` | не написаны | Реализация ветки (writing-plans). |
| Рантайм `abctl` | не подготовлен | Локально, за учётными данными; CI никогда не применяет. |
| CI умеет только `fmt`/`validate`/drift, но не `plan` | по замыслу (нет достижимого API без инстанса) | Не долг для исправления — задокументированное ограничение. Реальный `plan` живёт на opt-in локальном пути. |
| Сохранение STATUS (ход 2026-07-23) | пропущено | Был DISK-CRITICAL (5Gi < 10Gi минимум). Перезапустите `/update-session-environment` после `/clean-disk`. |

## Что ГОТОВО (не долг)

- `airbyte_emit.py validate` — реально, зелёное против живого реестра из 591 коннектора, с негативными тестами.
- Pre-commit-гейт `src/scripts/airbyte-blocks-check.sh` — срабатывает на `spec/sources/` или на ветке; самоотключается вне машины.
- Настройки, рецепты Justfile, юнит-тесты.
