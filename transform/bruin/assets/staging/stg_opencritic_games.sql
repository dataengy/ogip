/* @bruin
name: staging.stg_opencritic_games
type: duckdb.sql
materialization:
  type: table
owner: data-eng@ogip
tags: [staging, opencritic, daily]
depends:
  - raw.opencritic__game
columns:
  - name: game_id
    type: varchar
    checks: [{name: not_null}, {name: unique}]
  - name: name
    type: varchar
    checks: [{name: not_null}]
  - name: score
    type: integer
    checks: [{name: between, args: [0, 100]}]
  - name: review_count
    type: integer
    checks: [{name: non_negative}]
@bruin */
select
    game_id
    , slug
    , name
    , try_cast(released as date) as released_date
    , genre
    , publisher
    , cast(score as integer) as score
    , cast(review_count as integer) as review_count
    , content_hash
    , source_url
    , cast(_ingested_at as timestamp) as ingested_at
    , etl_batch_id
from raw.opencritic__game
