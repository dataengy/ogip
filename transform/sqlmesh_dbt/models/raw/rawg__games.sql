{{ config(materialized='view', tags=['raw', 'rawg', 'daily']) }}

SELECT
  *
FROM READ_PARQUET('./.run/data/raw/rawg__games/*.parquet')
