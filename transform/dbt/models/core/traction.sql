{{ config(materialized='table', schema='core', tags=['core', 'feature', 'daily']) }}

SELECT
  b.game_sk,
  CAST(sc.current_players AS BIGINT) AS current_players,
  CAST(sc.peak_24h AS BIGINT) AS peak_24h,
  CAST(sc.peak_all AS BIGINT) AS peak_all
FROM {{ ref('stg_game_match') }} AS b
LEFT JOIN {{ ref('stg_steamcharts_apps') }} AS sc
  ON REGEXP_REPLACE(LOWER(sc.name), '[^a-z0-9]', '', 'g') = b.match_key
