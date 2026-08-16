<!-- ru-translation-of: docs/adr/ADR-0019-odts-dq-projection-and-seven-prefect-subprojects.md sha:1a413e75b2f4 -->
<!-- Автоперевод. Источник — docs/adr/ADR-0019-odts-dq-projection-and-seven-prefect-subprojects.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0019-odts-dq-projection-and-seven-prefect-subprojects.md](ADR-0019-odts-dq-projection-and-seven-prefect-subprojects.md)

# ADR-0019 — Проекция DQ из ODTS в аудиты SQLMesh + семь разделённых Prefect-подпроектов

- **Status:** Accepted
- **Date:** 2026-07-23
- **Relates to:** [ADR-0004](ADR-0004-sqlmesh-default-transform-engine.md) ·
  [ADR-0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md) ·
  [ADR-0007](ADR-0007-prefect-orchestration.md) ·
  [ADR-0016](ADR-0016-odts-authoring-format-spec-sql.md) ·
  [ADR-0017](ADR-0017-odos-normative-profile.md) ·
  [ADR-0018](ADR-0018-odts-normative-profile.md) ·
  [план transform-expansion](../superpowers/plans/2026-07-23-transform-expansion-and-six-prefect-subprojects.md)

## Context

На production-пути существовали два независимых расхождения (drift), оба закрытые одним объёмом
работ (issue #37):

**DQ был описан, но не спроецирован.** `spec/sql` `columns[].checks:` — это словарь DQ из
ODTS §5-6 (`not_null`, `unique`, `non_negative`, `between`, `accepted_values`, плюс составной
`unique` верхнего уровня), и `spec/ODTS/IMPLEMENTATION.md` уже документировал — опережая код —
что это проецируется в «тесты dbt `schema.yml`, проверки Bruin, аудиты SQLMesh». Адаптеры dbt
и Bruin это соблюдали; `to_sqlmesh._model_text` — нет: он выдавал только `MODEL(name, kind)` и
тело SQL, молча отбрасывая каждую запись `columns.checks`. SQLMesh — production-движок
(ADR-0004), так что ограничение, которое соблюдал каждый другой адаптер, на пути, реально
работающем в production, было декоративной документацией без рантайм-эффекта. Четыре из пяти
raw-источников к тому же упирались в тупик на staging — core/fs потребляли только хребет rawg —
так что и проецировать было сравнительно мало DQ-поверхности.

**Оркестрация была шестью модулями, разделяющими один файл, а не шестью деплоями.**
`pipelines/flows/` содержал `engines/prefect_{sqlmesh,dbt,bruin,dagster,opendbt,sqlmesh_dbt}.py`,
каждый — однострочная обёртка над `make_engine_flow` в общем `pipelines/flows/_common.py`, без
`prefect.yaml` и без пер-конфигурационных `deployments/`. Ничего нельзя было `prefect deploy` для
одного движка без импорта всего пакета `pipelines.flows`, а профиль plain-SQL (`prefect-sql`) не
имел подпроекта вообще — шесть именованных конфигураций покрывали семь run-профилей.

## Decision

**DQ:** `to_sqlmesh.py` теперь рендерит каждую проверку `@bruin` в предложение `audits (...)`
блока `MODEL(...)` (`not_null → not_null(columns := (c))`, `unique → unique_values(columns
:= (c))`, `non_negative → accepted_range(min_v := 0)`, `between(a,b) → accepted_range(min_v :=
a, max_v := b)`, `accepted_values(...) → accepted_values(is_in := (...))`, составной верхнего
уровня `unique(columns: [...]) → unique_combination_of_columns(...)`). Отображение тотально и
fail-loud: имя проверки вне этого словаря вызывает `SqlSpecError` во время компиляции — ODTS
SPEC.md §5 «атрибуты вне словаря проверок ДОЛЖНЫ приводить к провалу компиляции» — и никогда не
молчаливый сброс. Затем проверки были описаны исчерпывающе по raw/staging/core/fs (сегодня
70 аудитов), опираясь на работу по lineage из Части 1 (мост нормализации заголовков
`staging.stg_game_match` плюс `core.{critic_reception,console_pricing,traction}`, так что все
пять источников теперь достигают `fs.market_features`).

**Проверки ≠ мониторы (ODTS §6).** Нижние пороги количества строк и окна свежести не являются
ограничениями корректности и были намеренно оставлены вне `columns[].checks:`. Они объявлены как
данные в [`spec/dq/policy.yml`](../../spec/dq/policy.yml) и загружаются + отчитываются
(подсчёт, печать сводки, выход 0) в [`dq/run.py`](../../dq/run.py). Это загружающе-отчитывающий
раннер, а не исполнитель — он не запрашивает хранилище и не оценивает порог. Исполнитель
(запрос к DuckDB, оценка `min_rows`/`max_age_hours`, запись в `platform_meta.dq_results`, модель
серьёзности ADR-0008: `error` блокирует, `warn` фиксирует) выходит за рамки этой работы и придёт
в Фазе 4.

**Оркестрация:** общая библиотека шагов переехала один раз, в `pipelines/_shared/` (`steps.py` —
`ingest_raw`, `build_warehouse`, `build_ml_outputs`, `publish_outputs`, `make_engine_flow`;
`alerting.py` — `notify_flow_failure`; `paths.py` — константы, относительные к репозиторию;
`engines.py` — `ENGINE_FLOWS`, карта transform-имя → модуль-подпроект). Каждый run-профиль стал
собственной директорией, `pipelines/<engine>/{__init__.py, flow.py, prefect.yaml}`, отдельно
`prefect deploy`-абельной без затягивания остальных шести: `sqlmesh` (production по умолчанию),
`plain_sql`, `dbt`, `opendbt`, `sqlmesh_dbt`, `bruin`, `dagster` — **семь**, а не шесть, как
только `plain_sql` получил собственный подпроект наряду с остальными пятью SQL-движками плюс
`dagster`. `pipelines/flows/engines/`, `pipelines/flows/_common.py`, `pipelines/flows/_paths.py`
и `pipelines/alerting_hooks.py` были удалены, как только их перестало что-либо импортировать;
`pipelines/flows/main.py` уцелел только как ре-экспорт `ingest_transform_publish` из
`pipelines.sqlmesh.flow`, потому что `src/ogip/tasks/integrations.py` запускает
`python -m pipelines.flows.main` и эта точка входа должна оставаться импортируемой по своему
историческому пути. `pipelines/dagster/flow.py` сохраняет Prefect как внешний оркестратор, а
связку dlt+dbt запускает *под* Dagster (`dg launch`) — единственный подпроект, не являющийся
чистым SQL-раннером.

## Consequences

- Положительное: DQ, объявленный один раз в `spec/sql`, теперь имеет один реальный рантайм-эффект
  на production-движке, а не только на движках сравнения (dbt/Bruin), которые и так его соблюдали;
  неизвестное имя проверки — ошибка на этапе сборки, а не проверка, чьё исчезновение никто не
  заметил.
- Положительное: каждый run-профиль независимо деплоится (`prefect deploy` из своей директории),
  и профиль plain-SQL больше не второсортный гражданин без подпроекта.
- Положительное: граница проверки≠мониторы структурна, а не соглашение об именовании — мониторы
  физически не могут появиться в `spec/sql` `checks:`, потому что словарь, рендерящийся в аудиты,
  не распознаёт имена `freshness`/`row_count` (они вызвали бы `SqlSpecError`).
- **Известный пробел, заметный by design:** `make check` (`just check` → `just test` → `pytest -m
  "not integration and not e2e"`) никогда не планирует и не применяет SQLMesh к реальному
  хранилищу, так что сгенерированные предложения `audits (...)` объявлены, но не *оцениваются*
  дефолтным gate. Только `uv run pytest src/tests/e2e/test_all_setups.py::test_base_setup_builds_and_produces_ml
  -k sqlmesh` (помеченный `e2e`, исключённый из `make check`) или живой запуск `prefect-sqlmesh`
  реально их исполняет. Это не гипотетика: во время этой работы аудит `not_null(locale)`
  на `core.console_pricing` падал для каждой игры rawg без листинга PSN (LEFT JOIN по
  несовпавшей игре давал строку из одних null) — `make check` всё это время оставался зелёным,
  и поломка была поймана только e2e-запуском SQLMesh (исправлено в коммите `d3caf76`, «fix(spec):
  console_pricing must not emit all-null rows for unmatched games»). Закрытие этого пробела —
  встраивание шага, исполняющего аудиты, в `make check` или эквивалентный быстрый pre-push gate —
  не является частью этого решения и остаётся открытой последующей работой.
- Отрицательное: `dq/run.py`, отчитывающийся о мониторах без их исполнения, — это вторая,
  иначе оформленная версия того же пробела (объявленный DQ без принуждения на дефолтном пути) —
  отслеживается как Фаза 4, здесь не закрыто.
- Нейтральное: `pipelines/_shared/engine_flow.py`, `pipelines/_shared/ingest.py` и пер-источниковые
  `@materialize`-ассеты скрейпера, описанные в исходном тексте плана transform-expansion, не
  вышли как отдельные модули — `make_engine_flow` и шаг ingestion остались в `steps.py`.
  Поведение соответствует замыслу плана; разбивка на файлы — нет.

## Alternatives considered

- **Оставить `to_sqlmesh` молчащим по проверкам, добавить отдельный слой DQ только для SQLMesh.**
  Отклонено — это означало бы, что SSoT (`spec/sql`) больше не описывает production-DQ, вновь
  вводя ровно то пер-движковое ручное дублирование, для предотвращения которого существует
  ADR-0005.
- **Свернуть мониторы количества строк/свежести в `checks:` ради единой поверхности спецификации.**
  Отклонено согласно ODTS §6: мониторы и проверки корректности имеют разную семантику отказа
  (монитор оценивается по состоянию wall-clock/объёма, а не по построчному предикату) и разные
  места by design; спецификация явно исключает их из `checks:`.
- **Сохранить один пакет `pipelines/flows/engines/` вместо семи директорий верхнего уровня.**
  Отклонено — модель `prefect deploy` в Prefect директория-ориентирована (`prefect.yaml` +
  `deployments/`); общий пакет не может выразить «деплой только конфигурации sqlmesh» без
  деплоя всего либо ручной фильтрации точек входа, что подрывает цель разделения.
- **Встроить e2e-запуск аудитов SQLMesh в `make check` сейчас, немедленно закрыв пробел.**
  Отклонено для этого изменения — e2e-набор гоняет реальные ingestion/warehouse-сборки на каждый
  движок и намеренно медленен и помечен `e2e` именно поэтому; вкладывание его в дефолтный gate —
  отдельное решение о бюджете времени gate, оставленное открытым, а не принятое здесь неявно.
