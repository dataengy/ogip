/* @odts 0.1
model     staging.stg_metacritic_games
kind      table
owner     data-eng@ogip
tags      staging, metacritic, daily

columns:
  slug        varchar   !null unique
  name        varchar   !null
  metascore   integer   non_negative
*/
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
