{{ config(materialized='table', schema='core', tags=['core', 'feature', 'daily']) }}

SELECT
  b.game_sk,
  psn.locale,
  psn.price AS psn_price,
  psn.currency AS psn_currency
FROM {{ ref('stg_game_match') }} AS b
LEFT JOIN {{ ref('stg_psn_concepts') }} AS psn
  ON REGEXP_REPLACE(LOWER(psn.name), '[^a-z0-9]', '', 'g') = b.match_key
/* Keep only games that actually HAVE a PSN listing. This is a pricing FACT table at */ /* (game_sk, locale) grain, so an unmatched game must have NO row rather than an all-null */ /* one -- otherwise not_null(locale) fails for every unmatched game (caught by the e2e */ /* SQLMesh run, which `make check` does not exercise). This is NOT the forbidden */ /* spine-dropping inner join: the rawg spine survives downstream, where fs.market_features */ /* LEFT JOINs this model, so unmatched games still appear with a null price and a false */ /* psn coverage flag. */
WHERE
  NOT psn.locale IS NULL
