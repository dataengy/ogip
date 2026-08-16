# Techdebt — finalization TBD-disable register (2026-07-30)

> 🇷🇺 Русская версия: [finalization-tbd.ru.md](finalization-tbd.ru.md)

One row per feature deliberately frozen during the finalization run
([plan](../superpowers/plans/2026-07-30-finalization-land-everything.md) ·
[umbrella task](../../.ai/tasks/finalization.md)). Rule: "defer, don't fake" — a frozen
feature fails **loudly** (banner, exit 2, `NotImplementedError`) and carries an issue;
never a silent no-op.

| # | Feature | Freeze mechanics | Issue | Unfreeze when |
|---|---|---|---|---|
| 1 | sqlmesh_dbt heavy e2e | behind `OGIP_E2E_ALL_ENGINES=1` + `pytest.mark.skip(reason="TBD #42")` | [#42](https://github.com/dataengy/ogip/issues/42) → P3 | the engine leaves `experimental/` |
| 2 | sqlmesh / opendbt / plain_sql profiles | `experimental: true` in `config/config.yml` + runner banner; out of default gates; docs say comparison-only | [#40](https://github.com/dataengy/ogip/issues/40) | a profile is re-promoted |
| 3 | Dagster ingestr CDC | label TBD/P3; stubs raise `NotImplementedError("TBD #13")` | [#13](https://github.com/dataengy/ogip/issues/13) | a CDC-shaped source materializes |
| 4 | Airbyte runtime | NO-GO guard in recipes (loud exit + eval-doc link); evaluation verdict stands | [#41](https://github.com/dataengy/ogip/issues/41) | ≥20 GiB disk + a provider-fit source |
| 5 | Resilient-scraping deferred verbs (async · throttle/backoff · circuit-breaker+DLQ · landing upsert · watermarks · parse pool · fetch obs · recorded-response test) | DEFERRED checklist in the issue body; code claims nothing it does not do | [#18](https://github.com/dataengy/ogip/issues/18) | source volume demands it |
| 6 | `integrations/prefect/{deploy,trigger}.py` + alerting SSoT routing | 5-line stubs exit 2 with "TBD" + issue ref, so `just prefect-deploy` / `deploy/vps/smoke.sh` fail loudly, not with FileNotFound | [#11](https://github.com/dataengy/ogip/issues/11) · [#17](https://github.com/dataengy/ogip/issues/17) | Prefect run model pinned + R2 live |
| 7 | ODTS 0.2 proposals | committed under `spec/ODTS/proposals/` behind a pre-normative banner; no version bump | [#35](https://github.com/dataengy/ogip/issues/35) · [#36](https://github.com/dataengy/ogip/issues/36) | 0.2 drafting opens |
| 8 | Prefect server+worker run model | ephemeral pinned as a decision comment in `config/config.yml`; server profile deferred to V2 scope | [#17](https://github.com/dataengy/ogip/issues/17) | a real VPS deploy is scheduled |
| 9 | DQ results recording (`platform_meta.dq_results`) | executor SHIPPED 2026-07-30 (row_count+freshness run against DuckDB; error-severity failure → exit 1; in `make check` — skips loudly without a warehouse — and in the CI e2e step). Only the Postgres recording of results remains deferred | [#43](https://github.com/dataengy/ogip/issues/43) | Postgres `platform_meta` lands (V2 scope) |
