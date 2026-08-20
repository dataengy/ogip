<!-- ru-translation-of: docs/techdebt/finalization-tbd.md sha:b300eda6daa9 -->
<!-- Автоперевод. Источник — docs/techdebt/finalization-tbd.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [finalization-tbd.md](finalization-tbd.md)

# Техдолг — реестр TBD-отключений финализации (2026-07-30)

Одна строка на каждую фичу, намеренно замороженную во время прогона финализации
([план](../superpowers/plans/2026-07-30-finalization-land-everything.md) ·
[зонтичная задача](../../.ai/tasks/finalization.md)). Правило: «откладывай, не имитируй»
(defer, don't fake) — замороженная фича падает **громко** (баннер, exit 2,
`NotImplementedError`) и несёт issue; никогда — тихий no-op.

| # | Фича | Механика заморозки | Issue | Разморозить, когда |
|---|---|---|---|---|
| 1 | тяжёлый e2e sqlmesh_dbt | за `OGIP_E2E_ALL_ENGINES=1` + `pytest.mark.skip(reason="TBD #42")` | [#42](https://github.com/dataengy/ogip/issues/42) → P3 | движок покинет `experimental/` |
| 2 | профили sqlmesh / opendbt / plain_sql | `experimental: true` в `config/config.yml` + баннер в раннере; вне дефолтных гейтов; доки говорят «только для сравнения» | [#40](https://github.com/dataengy/ogip/issues/40) | профиль будет снова повышен |
| 3 | Dagster ingestr CDC | метка TBD/P3; заглушки бросают `NotImplementedError("TBD #13")` | [#13](https://github.com/dataengy/ogip/issues/13) | появится источник CDC-формы |
| 4 | Рантайм Airbyte | NO-GO-guard в рецептах (громкий exit + ссылка на док оценки); вердикт оценки в силе | [#41](https://github.com/dataengy/ogip/issues/41) | ≥20 GiB диска + источник, подходящий под провайдера |
| 5 | Отложенные механики устойчивого скрейпинга (async · throttle/backoff · circuit-breaker+DLQ · upsert в landing · вотермарки · пул парсинга · наблюдаемость fetch · тест на записанных ответах) | чек-лист DEFERRED в теле issue; код не заявляет ничего, чего не делает | [#18](https://github.com/dataengy/ogip/issues/18) | объём источников этого потребует |
| 6 | `integrations/prefect/{deploy,trigger}.py` + SSoT-маршрутизация алертинга | 5-строчные заглушки выходят с кодом 2 и "TBD" + ссылкой на issue, так что `just prefect-deploy` / `deploy/vps/smoke.sh` падают громко, а не с FileNotFound | [#11](https://github.com/dataengy/ogip/issues/11) · [#17](https://github.com/dataengy/ogip/issues/17) | модель запуска Prefect зафиксирована + R2 живой |
| 7 | Предложения ODTS 0.2 | закоммичены в `spec/ODTS/proposals/` за пред-нормативным баннером; без повышения версии | [#35](https://github.com/dataengy/ogip/issues/35) · [#36](https://github.com/dataengy/ogip/issues/36) | откроется работа над черновиком 0.2 |
| 8 | Модель запуска Prefect server+worker | ephemeral зафиксирован комментарием-решением в `config/config.yml`; серверный профиль отложен в объём V2 | [#17](https://github.com/dataengy/ogip/issues/17) | будет запланирован реальный деплой на VPS |
| 9 | Запись результатов DQ (`platform_meta.dq_results`) | исполнитель ОТГРУЖЕН 2026-07-30 (row_count+freshness выполняются на DuckDB; сбой с severity error → exit 1; в `make check` — без хранилища громко скипается — и в CI e2e-шаге). Отложенной остаётся только запись результатов в Postgres | [#43](https://github.com/dataengy/ogip/issues/43) | приземлится Postgres `platform_meta` (объём V2) |
