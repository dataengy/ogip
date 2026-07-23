/* @odts 0.1
model     staging.stg_games
kind      table
owner     data-eng@ogip
tags      staging, rawg, daily

columns:
  game_id   integer   !null unique
  name      varchar   !null
*/
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
