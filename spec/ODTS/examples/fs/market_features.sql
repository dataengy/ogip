/* @odts 0.1
model     fs.market_features
kind      table
owner     data-eng@ogip
tags      fs, feature-store, daily

columns:
  game_sk            varchar   !null unique
  popularity_score   double    non_negative
*/
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
