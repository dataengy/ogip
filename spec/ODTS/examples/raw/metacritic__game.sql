/* @odts 0.1
model     raw.metacritic__game
kind      view
owner     data-eng@ogip
tags      raw, metacritic, daily

columns:
  slug           varchar   !null
  content_hash   varchar   !null
  source_url     varchar   !null
*/
select *
from read_parquet('.run/data/raw/metacritic__game/*.parquet')
