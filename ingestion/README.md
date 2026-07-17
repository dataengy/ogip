# `ingestion/`

Reusable ingestion abstractions and per-source pipelines (ADR-0006, D11). **dlt** is the
default engine; scraped/parsed data lands in the Postgres `landing` schema first.

| Subdir | Holds |
|---|---|
| `base/` | `BaseSource` · `ApiSource` · `ScraperSource` · `IncrementalSource` (produce dlt resources) |
| `common/` | shared httpx client, throttle (rate limits), cache, watermark store |
| `sources/` | `rawg.py` (M0) · `steam.py` · `steam_reviews.py` · `igdb.py` · `reddit.py` · `twitch.py` · `hltb.py` · `metacritic.py` |

Every source demonstrates pagination · retries · rate limits · incremental sync · watermark ·
cache · error handling, landing **raw Parquet** (Layer 0, `<system>__<table>`). _Built from Phase 2._
