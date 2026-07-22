{{ config(materialized='table', schema='core', tags=['core', 'feature', 'daily']) }}

SELECT
  b.game_sk,
  psn.locale,
  psn.price AS psn_price,
  psn.currency AS psn_currency
FROM {{ ref('stg_game_match') }} AS b
LEFT JOIN {{ ref('stg_psn_concepts') }} AS psn
  ON REGEXP_REPLACE(LOWER(psn.name), '[^a-z0-9]', '', 'g') = b.match_key
