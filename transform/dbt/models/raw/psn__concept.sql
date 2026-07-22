{{ config(materialized='view', tags=['raw', 'psn', 'daily']) }}

SELECT
  *
FROM READ_PARQUET('./.run/data/raw/psn__concept/*.parquet')
