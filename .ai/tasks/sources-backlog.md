# Task — Sources backlog: candidates mapped to games-market models

**Status:** 📋 backlog (grooming) · **Priority:** P2

Candidate sources for extending coverage, mapped to the market-intelligence use cases the
outputs serve: **pricing · scope/length · production budget · traction/attention ·
quality**. Every source enters production only through the standard path: ODCS contract →
`BaseSource`/`ScraperSource` → landing/raw → spec models
([ADR-0006](../../docs/adr/ADR-0006-dlt-default-ingestion-postgres-landing.md) ·
[ADR-0014](../../docs/adr/ADR-0014-resilient-scraping-concurrency.md)).

## Shipped

| Source | Mode | Feeds |
|---|---|---|
| RAWG | API (dlt-direct) | catalog backbone: games, genres, platforms, ratings (M0) |

## Candidates (proposed order)

| # | Source | Endpoints / data | Mode | Feeds (use case) |
|---|---|---|---|---|
| 1 | **Steam Store API** | appdetails; per-region prices (`cc=`) | API; volume-hostile sweeps | regional pricing · PC catalog truth |
| 2 | **Steam Reviews API** | review stream per app | API, paginated | quality/sentiment · traction time series |
| 3 | ~~**HLTB**~~ | ~~main / extra / completionist hours~~ | **⛔ FORBIDDEN** — [robots/ToS](../../spec/sources/games/hltb_games.yaml) bans automated retrieval + AI/ML datasets (2026-07-18) | scope/length needs a licensed substitute (IGDB `time_to_beat`, Wikidata) |
| 4 | **Metacritic / OpenCritic** | critic + user scores | scrape — **now the P1 slice**; both [probe-verified](../../spec/sources/games/) (JSON-LD) | quality dimension |
| 5 | **IGDB** (Twitch OAuth) | games, companies, franchises, dates | API | entity-resolution backbone · company graph |
| 6 | **SteamSpy** | ownership/sales estimates | API (rate-limited) | market sizing · sales proxies |
| 7 | **Twitch API** | streams/viewership per game | API | attention/traction time series |
| 8 | **MobyGames** | credits → team size per game | API (keyed, strict limits) | production-scale/budget proxies |
| 9 | **Wikidata / Wikipedia** | budgets, dates, studios | API/dumps | budget calibration · entity enrichment |
| 10 | **Reddit** | subreddit activity per game | API | community traction |
| 11 | **SteamCharts / player counts** | concurrent-players history | scrape — [probe-verified](../../spec/sources/games/steamcharts_app.yaml) (css markers; no robots.txt declared) | traction time series |
| 12 | **Kickstarter** | disclosed campaign budgets | scrape / datasets — ⚠️ Cloudflare challenge on `robots.txt` itself (403, 2026-07-18): hostile to automation, prefer published datasets | indie budget calibration |
| 13 | **itch.io** | indie long-tail catalog | API | indie market coverage |

## Grooming rules

- Promoting a candidate = its own task file + ODCS contract draft + ToS/robots review
  (ADR-0014 politeness) + an effort estimate (keeps per-source scoping honest).
- Prefer sources that unlock a **new model dimension** (pricing, scope, budget, traction,
  quality) over more-of-the-same metadata.
- The PLAN A6 list (Steam · RAWG · IGDB · Reddit · Twitch · HLTB · Metacritic) stays the
  committed core; rows 6 and 8–13 are extensions pending the volume/ToS review
  ([OPEN-QUESTIONS §1–§2](../../docs/OPEN-QUESTIONS.md)).
