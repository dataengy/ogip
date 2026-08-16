<!-- ru-translation-of: docs/adr/ADR-0006-dlt-default-ingestion-postgres-landing.md sha:bb9de3d8bccf -->
<!-- Автоперевод. Источник — docs/adr/ADR-0006-dlt-default-ingestion-postgres-landing.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0006-dlt-default-ingestion-postgres-landing.md](ADR-0006-dlt-default-ingestion-postgres-landing.md)

# ADR-0006 — dlt как ingestion по умолчанию + посадка в Postgres; ingestr опционален (CDC)

- **Статус:** Принято
- **Дата:** 2026-07-17
- **Связано с:** D11 · [ADR-0008](ADR-0008-postgresql-roles.md) · `docs/comparisons/dlt-vs-ingestr.md`

## Контекст

Ряд целевых API враждебны/недокументированы (лимиты Steam, OAuth2 у IGDB, скрейпинг
HLTB/Metacritic). Скрейпенные/распарсенные данные грязны и выигрывают от долговечного, запрашиваемого
буфера, прежде чем стать неизменяемой сырой записью.

## Решение

**dlt** — движок ingestion по умолчанию (через семейство `BaseSource`). Два паттерна: чистые API
идут **dlt-direct** → raw Parquet; скрейпенные/распарсенные данные сначала садятся в схему **PostgreSQL `landing`**,
затем **dlt** (по умолчанию) — либо **ingestr** (опционально, для CDC) — загружают их в raw Parquet.

## Последствия

- Повторы/переобработка скрейпенных данных дёшевы; шаг загрузки получает чистый, типизированный источник.
- ingestr/CDC доступны для будущего near-real-time захвата без переархитектуры.

## Рассмотренные альтернативы

- **Airbyte как основной** — отменено: low-code-коннекторы не подходят враждебным API; удалён из ядра.
- **ingestr по умолчанию** — оставлен опциональным; dlt даёт больше Python-контроля для кастомных источников.
