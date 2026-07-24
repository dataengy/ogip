/* @odts 0.1
model     core.game
kind      table
owner     data-eng@ogip
tags      core, entity, daily

columns:
  game_sk   varchar   pk !null unique
  title     varchar   !null
*/
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
