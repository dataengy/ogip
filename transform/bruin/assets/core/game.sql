/* @bruin
name: core.game
type: duckdb.sql
materialization:
  type: table
owner: data-eng@ogip
tags: [core, entity, daily]
depends:
  - staging.stg_games
columns:
  - name: game_sk
    type: varchar
    primary_key: true
    checks: [{name: not_null}, {name: unique}]
  - name: title
    type: varchar
    checks: [{name: not_null}]
  - name: metacritic
    type: integer
    checks: [{name: between, args: [0, 100]}]
@bruin */
select
    md5(cast(game_id as varchar)) as game_sk
    , game_id
    , name as title
    , slug
    , released_date
    , extract(year from released_date) as release_year
    , rating
    , ratings_count
    , metacritic
    , playtime_hours
    , added_count
from staging.stg_games
