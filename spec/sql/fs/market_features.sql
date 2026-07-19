/* @bruin
name: fs.market_features
type: duckdb.sql
materialization:
  type: table
owner: data-eng@ogip
tags: [fs, feature-store, daily]
depends:
  - core.game
columns:
  - name: game_sk
    type: varchar
    checks: [{name: not_null}, {name: unique}]
  - name: popularity_score
    type: double
    checks: [{name: not_null}, {name: non_negative}]
@bruin */
select
    game_sk
    , game_id
    , title
    , release_year
    , rating
    , ratings_count
    , metacritic
    , playtime_hours
    , added_count
    , coalesce(rating, 0) * ln(1 + coalesce(ratings_count, 0)) as popularity_score
    , coalesce(metacritic, 0) / 100.0 as critic_score
from core.game
