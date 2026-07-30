{{ config(materialized='table', schema='core', tags=['core', 'entity', 'daily']) }}

SELECT
  MD5(CAST(game_id AS TEXT)) AS game_sk,
  game_id,
  name AS title,
  slug,
  released_date,
  EXTRACT(YEAR FROM released_date) AS release_year,
  rating,
  ratings_count,
  metacritic,
  playtime_hours,
  added_count
FROM {{ ref('stg_games') }}
