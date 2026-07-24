{{ config(materialized='view', tags=['raw', 'metacritic', 'daily']) }}

SELECT
  *
FROM READ_PARQUET('./.run/data/raw/metacritic__game/*.parquet')
