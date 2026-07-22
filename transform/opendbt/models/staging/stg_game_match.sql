{{ config(materialized='view', schema='staging', tags=['staging', 'bridge', 'daily']) }}

WITH spine AS (
  SELECT
    MD5(CAST(game_id AS TEXT)) AS game_sk,
    REGEXP_REPLACE(LOWER(name), '[^a-z0-9]', '', 'g') AS match_key
  FROM {{ ref('stg_games') }}
)
SELECT
  game_sk,
  match_key
FROM spine
