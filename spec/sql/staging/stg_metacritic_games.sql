/* @bruin
name: staging.stg_metacritic_games
type: duckdb.sql
materialization:
  type: table
owner: data-eng@ogip
tags: [staging, metacritic, daily]
depends:
  - raw.metacritic__game
columns:
  - name: slug
    type: varchar
    checks: [{name: not_null}, {name: unique}]
  - name: name
    type: varchar
    checks: [{name: not_null}]
  - name: metascore
    type: integer
    checks: [{name: non_negative}]
@bruin */
select
    slug
    , name
    , try_cast(released as date) as released_date
    , genre
    , publisher
    , cast(metascore as integer) as metascore
    , cast(review_count as integer) as review_count
    , content_hash
    , source_url
    , cast(_ingested_at as timestamp) as ingested_at
    , etl_batch_id
from raw.metacritic__game
