{{ config(materialized='table', schema='staging', tags=['staging', 'opencritic', 'daily']) }}

SELECT
  game_id,
  slug,
  name,
  TRY_CAST(released AS DATE) AS released_date,
  genre,
  publisher,
  CAST(score AS INT) AS score,
  CAST(review_count AS INT) AS review_count,
  content_hash,
  source_url,
  CAST(_ingested_at AS TIMESTAMP) AS ingested_at,
  etl_batch_id
FROM {{ ref('opencritic__game') }}
