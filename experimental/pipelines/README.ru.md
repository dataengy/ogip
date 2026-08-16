<!-- ru-translation-of: experimental/pipelines/README.md sha:a2330bd5c7d6 -->
<!-- Автоперевод. Источник — experimental/pipelines/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# `experimental/pipelines/` — сравнительные / R&D transform-сетапы

Отдельно деплоящиеся Prefect-подпроекты для transform-движков, **не** являющихся двумя
основными кандидатами сравнения. Вне пути `make`/пайплайна по умолчанию (re-root, ADR-0020, #40).

| Подпроект | Сетап | Статус |
|---|---|---|
| `sqlmesh/` | Prefect + SQLMesh (был продакшен-дефолтом) | экспериментальный |
| `plain_sql/` | Prefect + runner на чистом SQL | экспериментальный |
| `opendbt/` | Prefect + OpenDBT (расширенный dbt-core) | экспериментальный |
| `sqlmesh_dbt/` | Prefect + SQLMesh-over-dbt | экспериментальный (heavy-e2e сломан — #42) |
| `dagster/` | Dagster (dlt+dbt), обёрнутый в Prefect | экспериментальный |

Каждый — это `{__init__.py, flow.py, prefect.yaml}`, импортирующий общую библиотеку шагов из
`pipelines._shared`; по форме идентичен основным подпроектам в `pipelines/`, отличается только
расположение. Реестр flow `pipelines._shared.engines.ENGINE_FLOWS` отображает каждый в
`experimental.pipelines.<engine>.flow`.

Два **основных** кандидата — **dbt** и **bruin** — живут в `pipelines/`, и именно их гоняют
`make check` / e2e по умолчанию. Эти сравнительные движки запускаются только под
`OGIP_E2E_ALL_ENGINES=1`.
