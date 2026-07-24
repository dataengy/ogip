{{ config(materialized='table', schema='core', tags=['core', 'feature', 'daily']) }}

SELECT
  b.game_sk,
  mc.metascore AS metacritic_score,
  oc.score AS opencritic_score
FROM {{ ref('stg_game_match') }} AS b
LEFT JOIN {{ ref('stg_metacritic_games') }} AS mc
  ON REGEXP_REPLACE(LOWER(mc.name), '[^a-z0-9]', '', 'g') = b.match_key
LEFT JOIN {{ ref('stg_opencritic_games') }} AS oc
  ON REGEXP_REPLACE(LOWER(oc.name), '[^a-z0-9]', '', 'g') = b.match_key
