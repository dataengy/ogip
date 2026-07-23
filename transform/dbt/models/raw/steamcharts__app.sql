{{ config(materialized='view', tags=['raw', 'steamcharts', 'daily']) }}

SELECT
  *
FROM READ_PARQUET('./.run/data/raw/steamcharts__app/*.parquet')
