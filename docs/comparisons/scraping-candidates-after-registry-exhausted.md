# Scraping candidates once the scrape-tier registry is built out

- **Date:** 2026-07-23 · **Refs:** OGIP#18, OGIP#19
- **Context:** all four scrape-tier sources (`metacritic`, `opencritic`, `psn`, `steamcharts`)
  are already implemented (`ingestion/sources/*.py`, non-stub, with raw+staging models). The
  `psn` scraper is being refined by a parallel session. So "best scraping candidate" is no
  longer "which to build first" — it is "what next, and is it even a scrape".

## Ranking by value × legality × feasibility

The domain re-read (`.ai/newsletter.hushcrasher.com/SUMMARY.md`) fixes the value axis: the model's
two decisive variables are **credit length** (MobyGames) and **disk size / length** (HowLongToBeat).

| Candidate | Domain value | Verdict |
|---|---|---|
| **MobyGames** — credits | 🔴 highest (#1 model driver) | **Blocked** — ToS. See below. |
| **HowLongToBeat** — playtime | 🔴 highest (#2 driver) | **Blocked** — ToS. |
| **Gamalytic** — revenue | 🟠 high; named source, was absent | **Not a scrape — a keyless API.** See below. |
| SteamCharts (done) | — | best exemplar: the only genuine CSS-selector scrape in the registry |

## The blocked finding — state it, don't hide it

The two variables that most drive Hushcrasher's scope/budget model come from **MobyGames**
(credits) and **HowLongToBeat** (length). Both are ToS-blocked for OGIP's use
([[ogip-business-domain-framing]]). Therefore:

> OGIP can reproduce the *cheap* half of the scope taxonomy (disk size, language count — both
> reachable from Steam) and **none of the expensive half** (credits, curated playtime). This is a
> legal constraint, not an engineering gap, and it caps how closely the platform can mirror the
> reference model. It belongs in the platform's limitations doc, stated up front.

There is no scraping cleverness that fixes this — a permissible source has to appear, or the
variable stays out of the model.

## Gamalytic is an API, not a scrape

Probed live 2026-07-23:

- `api.gamalytic.com/steam-games/list?page=0&limit=1` → **HTTP 200, keyless**, `pages: 124522`,
  each row carrying `copiesSold` (a revenue proxy). Paginated — dlt `rest_api`'s exact shape.
- `api.gamalytic.com/game/{id}` → **403**, "requires an API key … upgrade to Starter or
  Professional". Detailed per-game data is paid.
- `gamalytic.com/robots.txt` → **429 + Vercel Security Checkpoint** (site is anti-bot; the API
  host is not).

So the highest-value *permissible* gap routes to **dlt, tier `direct`, `auth: none` for the list
endpoint** — not to a scraper. It is the single best next ingestion target, and it is not scraping.

## Recommendation

1. **No new scraper is warranted.** The scrape tail is built; the parallel session is finishing it.
2. **Gamalytic → dlt descriptor** (ingestion lane, handed off with the probe evidence above).
3. **Document the MobyGames/HLTB block** in the platform limitations doc — the honest cap on
   fidelity to the reference model.
