{{ config(materialized='table', schema='fs', tags=['fs', 'feature-store', 'daily']) }}

/* `core.console_pricing` grain is (game_sk, locale) across every PSN storefront, so a bare */ /* `min(psn_price)` mixes currencies (e.g. JPY vs USD) into one meaningless number. Restrict to */ /* the US/USD storefront (`en-us`) so the feature is single-currency and comparable, and keep */ /* the `group by` as a defense-in-depth grain guarantee (one row per game_sk) even though */ /* `core.console_pricing`'s own `unique(game_sk, locale)` check already makes at most one */ /* `en-us` row per game possible. A game with no `en-us` row yields NULL here — the coverage */ /* flag below already signals presence, so NULL is correct, not a gap. */
WITH pricing_by_game AS (
  SELECT
    game_sk,
    MIN(psn_price) AS psn_price_usd,
    MIN(psn_currency) AS psn_currency
  FROM {{ ref('console_pricing') }}
  WHERE
    locale = 'en-us'
  GROUP BY
    game_sk
)
SELECT
  g.game_sk,
  g.game_id,
  g.title,
  g.release_year,
  g.rating,
  g.ratings_count,
  g.metacritic,
  g.playtime_hours,
  g.added_count,
  COALESCE(g.rating, 0) * LN(1 + COALESCE(g.ratings_count, 0)) AS popularity_score,
  COALESCE(g.metacritic, 0) / 100.0 AS critic_score,
  cr.metacritic_score,
  cr.opencritic_score,
  CASE
    WHEN NOT cr.metacritic_score IS NULL AND NOT cr.opencritic_score IS NULL
    THEN (
      cr.metacritic_score + cr.opencritic_score
    ) / 2.0
    ELSE COALESCE(cr.metacritic_score, cr.opencritic_score)
  END AS avg_critic_score,
  pg.psn_price_usd,
  pg.psn_currency,
  tr.peak_all AS peak_players, /* `game_sk` on cr/pg/tr is projected from the bridge and is therefore NEVER null (every */ /* bridge row survives the LEFT JOIN inside the source model); the actual measured column */ /* IS null when the title match failed, so that is what a coverage flag has to test. */
  NOT COALESCE(cr.metacritic_score, cr.opencritic_score) IS NULL AS has_critic_reception,
  NOT pg.psn_price_usd IS NULL AS has_console_pricing,
  NOT tr.peak_all IS NULL AS has_traction
FROM {{ ref('game') }} AS g
LEFT JOIN {{ ref('critic_reception') }} AS cr
  ON g.game_sk = cr.game_sk
LEFT JOIN pricing_by_game AS pg
  ON g.game_sk = pg.game_sk
LEFT JOIN {{ ref('traction') }} AS tr
  ON g.game_sk = tr.game_sk
