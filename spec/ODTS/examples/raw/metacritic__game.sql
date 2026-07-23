/* @odts 0.1
model     raw.metacritic__game
kind      view
owner     data-eng@ogip
tags      raw, metacritic, daily
*/
select *
from read_parquet('.run/data/raw/metacritic__game/*.parquet')
