{{ config(materialized='table', schema='staging', tags=['staging', 'rawg', 'daily']) }}

SELECT
  id AS game_id,
  slug,
  name,
  TRY_CAST(released AS DATE) AS released_date,
  CAST(rating AS DOUBLE) AS rating,
  CAST(ratings_count AS INT) AS ratings_count,
  CAST(metacritic AS INT) AS metacritic,
  CAST(playtime AS INT) AS playtime_hours,
  CAST(added AS INT) AS added_count,
  CAST(_ingested_at AS TIMESTAMP) AS ingested_at,
  etl_batch_id
FROM {{ ref('rawg__games') }}
