<!-- ru-translation-of: docs/adr/ADR-0001-edw-layering-no-medallion.md sha:5aad27f5f855 -->
<!-- Автоперевод. Источник — docs/adr/ADR-0001-edw-layering-no-medallion.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0001-edw-layering-no-medallion.md](ADR-0001-edw-layering-no-medallion.md)

# ADR-0001 — Классическое разделение EDW на слои, без словаря medallion

- **Status:** Accepted
- **Date:** 2026-07-17
- **Relates to:** ARCHITECTURE · закон именования слоёв

## Context

Слоям нужны тестируемые контракты, а не ярлыки уровней качества. Названия «bronze/silver/gold»
обозначают уровень, но ничего не говорят ни о контрактах моделирования, ни о владении.

## Decision

Использовать классические слои EDW, каждый с жёстким контрактом и законом именования:
`0 raw <system>__<table>` → `1 stg_*` → `2 core` (3NF + частичный DV) → `3 *_fact/*_dim` (звезда
Kimball) → `4 am_<entity>_stream` (Activity Schema) → `5 owt_*/agg_*` (витрины) → `6 fs_*`
(feature store). Пропуск слоёв вниз запрещён. **Нигде никакого словаря medallion.**

## Consequences

- Каждый слой остаётся простым, независимо тестируемым и с чётким владением.
- Контрибьюторы обязаны соблюдать закон именования (проверяется структурным guard в CI).

## Alternatives considered

- **Medallion (bronze/silver/gold)** — отклонено: кодирует уровни качества, а не контракты моделирования.
