{{ config(materialized='table', schema='staging', tags=['staging', 'steamcharts', 'daily']) }}

SELECT
  appid,
  name, /* Layer-0 lands the counts AS-IS with thousands separators ("912,345"); strip and cast here. */
  TRY_CAST(REPLACE(current_players, ',', '') AS BIGINT) AS current_players,
  TRY_CAST(REPLACE(peak_24h, ',', '') AS BIGINT) AS peak_24h,
  TRY_CAST(REPLACE(peak_all, ',', '') AS BIGINT) AS peak_all,
  content_hash,
  source_url,
  CAST(_ingested_at AS TIMESTAMP) AS ingested_at,
  etl_batch_id
FROM {{ ref('steamcharts__app') }}
