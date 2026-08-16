<!-- ru-translation-of: docs/adr/ADR-0010-activity-model-layer.md sha:b8188672a72e -->
<!-- Автоперевод. Источник — docs/adr/ADR-0010-activity-model-layer.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0010-activity-model-layer.md](ADR-0010-activity-model-layer.md)

# ADR-0010 — Слой Activity Model (Activity Schema)

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** D13 · [ADR-0001](ADR-0001-edw-layering-no-medallion.md) · `docs/comparisons/modeling-techniques.md`

## Context

Звезда Кимбалла и частичный Data Vault хорошо моделируют сущности и факты, но вопросы вида
временных рядов «что делала эта сущность» (релиз, изменение цены, отзыв, стрим, упоминание)
неудобны, когда фактов много. [Activity Schema](https://www.activityschema.com/) моделирует всё
это как единый поток временных рядов.

## Decision

Добавить слой **Activity Model (AM)** (Layer 4): `am_<entity>_stream` — единый поток активностей
в стиле Activity Schema для каждой сущности (одна строка на активность: `entity_id`, `ts`,
`activity`, признаки, `activity_occurrence`, `activity_repeated_at`), построенный из CORE. Он
дополняет звезду Кимбалла STAR (обе над CORE) и питает MARTS/FS. Датасеты выводятся через
темпоральные соединения (первое/последнее/агрегат).

## Consequences

- Продемонстрированы четыре техники моделирования: 3NF · частичный Data Vault · Кимбалл · Activity Schema.
- Ещё один аналитический слой на сопровождение; оставлен исключительно на SQL (SQLMesh), без нового инструментария.

## Alternatives considered

- **Только Кимбалл** — упускает технику единого потока активностей, которую этот проект хочет продемонстрировать.
