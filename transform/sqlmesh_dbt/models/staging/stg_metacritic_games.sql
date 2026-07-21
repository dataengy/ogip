{{ config(materialized='table', schema='staging', tags=['staging', 'metacritic', 'daily']) }}

SELECT
  slug,
  name,
  TRY_CAST(released AS DATE) AS released_date,
  genre,
  publisher,
  CAST(metascore AS INT) AS metascore,
  CAST(review_count AS INT) AS review_count,
  content_hash,
  source_url,
  CAST(_ingested_at AS TIMESTAMP) AS ingested_at,
  etl_batch_id
FROM {{ ref('metacritic__game') }}
