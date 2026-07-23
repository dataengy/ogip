{{ config(materialized='table', schema='staging', tags=['staging', 'psn', 'daily']) }}

SELECT
  row_key,
  concept_id,
  locale,
  name,
  sku,
  category,
  TRY_CAST(price AS DOUBLE) AS price,
  currency,
  content_hash,
  source_url,
  CAST(_ingested_at AS TIMESTAMP) AS ingested_at,
  etl_batch_id
FROM {{ ref('psn__concept') }}
