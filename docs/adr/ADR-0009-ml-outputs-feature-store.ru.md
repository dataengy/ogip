<!-- ru-translation-of: docs/adr/ADR-0009-ml-outputs-feature-store.md sha:6488f92b341b -->
<!-- Автоперевод. Источник — docs/adr/ADR-0009-ml-outputs-feature-store.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0009-ml-outputs-feature-store.md](ADR-0009-ml-outputs-feature-store.md)

# ADR-0009 — Продукт = ML-ready-выходы + Feature Store; никакого BI/семантики в ядре

- **Статус:** Принято
- **Дата:** 2026-07-17
- **Связано с:** D6/D7/D8

## Контекст

Целевые пользователи — Data Scientists, ML-инженеры и аналитики, а не BI-пользователи. Продукт
платформы должен обслуживать моделирование, а не дашборды.

## Решение

Продукт — это **ML-ready Parquet-датасеты** плюс слой **Feature Store (`fs_*`)**
(SQL-как-feature-store → parquet). Демо-ноутбуки JupyterLab — основной интерфейс для DS;
`examples/load_datasets.py` показывает программную загрузку. Семантические слои (MetricFlow/Cube) и
BI (Evidence) — **опциональное исследование** в `experimental/`; отдельный инструмент FS (Feast/
Featureform) — проанализированный вариант, а не основная зависимость.

## Последствия

- Выходы загружаются напрямую (`pd/pl/duckdb.read_parquet`); нет семантического API для эксплуатации.
- Нет онлайн-подачи фичей до задокументированного внедрения инструмента FS.

## Рассмотренные альтернативы

- **BI-first + семантический слой** (OGAP) — отменено: неверная аудитория для этой платформы.
- **Отдельный feature store сейчас** — отложено в `docs/comparisons/feature-store-tools.md`.
