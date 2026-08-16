<!-- ru-translation-of: ingestion/README.md sha:36793fd1bd6f -->
<!-- Автоперевод. Источник — ingestion/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# `ingestion/`

Переиспользуемые абстракции инжеста и по-источниковые пайплайны (ADR-0006, D11). **dlt** —
движок по умолчанию; наскрейпленные/распарсенные данные сначала приземляются в Postgres-схему
`landing`.

| Подкаталог | Содержит |
|---|---|
| `base/` | `BaseSource` · `ApiSource` · `ScraperSource` · `IncrementalSource` (порождают dlt-ресурсы) |
| `common/` | общий httpx-клиент, троттлинг (rate limits), кэш, хранилище watermark |
| `sources/` | `rawg.py` (M0) · `steam.py` · `steam_reviews.py` · `igdb.py` · `reddit.py` · `twitch.py` · `hltb.py` · `metacritic.py` |

Каждый источник демонстрирует пагинацию · ретраи · rate limits · инкрементальную синхронизацию ·
watermark · кэш · обработку ошибок, приземляя **raw Parquet** (слой 0, `<system>__<table>`).
_Строится начиная с фазы 2._
