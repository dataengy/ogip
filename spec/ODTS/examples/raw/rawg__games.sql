/* @odts 0.1
model     raw.rawg__games
kind      view
owner     data-eng@ogip
tags      raw, rawg, daily
*/
select *
from read_parquet('.run/data/raw/rawg__games/*.parquet')
