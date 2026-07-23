{{ config(materialized='view', tags=['raw', 'opencritic', 'daily']) }}

SELECT
  *
FROM READ_PARQUET('./.run/data/raw/opencritic__game/*.parquet')
