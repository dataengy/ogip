{{ config(materialized='table', schema='fs', tags=['fs', 'feature-store', 'daily']) }}

SELECT
  game_sk,
  game_id,
  title,
  release_year,
  rating,
  ratings_count,
  metacritic,
  playtime_hours,
  added_count,
  COALESCE(rating, 0) * LN(1 + COALESCE(ratings_count, 0)) AS popularity_score,
  COALESCE(metacritic, 0) / 100.0 AS critic_score
FROM {{ ref('game') }}
