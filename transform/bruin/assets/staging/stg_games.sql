/* @bruin
name: staging.stg_games
type: duckdb.sql
materialization:
  type: table
owner: data-eng@ogip
tags: [staging, rawg, daily]
depends:
  - raw.rawg__games
columns:
  - name: game_id
    type: integer
    checks: [{name: not_null}, {name: unique}]
  - name: name
    type: varchar
    checks: [{name: not_null}]
  - name: ratings_count
    type: integer
    checks: [{name: non_negative}]
  - name: playtime_hours
    type: integer
    checks: [{name: non_negative}]
  - name: added_count
    type: integer
    checks: [{name: non_negative}]
@bruin */
select
    id as game_id
    , slug
    , name
    , try_cast(released as date) as released_date
    , cast(rating as double) as rating
    , cast(ratings_count as integer) as ratings_count
    , cast(metacritic as integer) as metacritic
    , cast(playtime as integer) as playtime_hours
    , cast(added as integer) as added_count
    , cast(_ingested_at as timestamp) as ingested_at
    , etl_batch_id
from raw.rawg__games
