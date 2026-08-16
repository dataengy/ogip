<!-- ru-translation-of: docs/adr/ADR-0021-orchestrator-transform-dq-boundary.md sha:22977d140173 -->
<!-- Автоперевод. Источник — docs/adr/ADR-0021-orchestrator-transform-dq-boundary.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0021-orchestrator-transform-dq-boundary.md](ADR-0021-orchestrator-transform-dq-boundary.md)

# ADR-0021 — Граница ответственности оркестратор/трансформации (без дублирования DQ в Dagster)

- **Статус:** Accepted
- **Дата:** 2026-07-19 (перенумерован с 0017 2026-07-30 — номер столкнулся с
  [ADR-0017-odos-normative-profile](ADR-0017-odos-normative-profile.md), написанным параллельно)
- **Связано с:** [ADR-0015](ADR-0015-dagster-alt-orchestration-dg-components.md) (альт-оркестрация Dagster),
  [ADR-0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md) (spec SSoT + компилятор),
  [ADR-0020](ADR-0020-dbt-bruin-primary-transform-engines.md) (dbt primary + Bruin co-primary движки трансформаций)

## Контекст

Альт-оркестрация Dagster (ADR-0015) связывает dbt/dlt-ассеты, джобы, расписания, сенсоры — и
обросла рукописным Dagster-`asset_check` (`market_features_nonempty_and_scored`), утверждающим
контракт FS-фичей (rows > 0, `popularity_score` не null). Это утверждение — *качество данных*,
а DQ уже принадлежит dbt: `spec/` (Bruin `checks:`) компилируется в dbt-тесты, `dbt build` их
запускает, и `dagster-dbt` **автоматически поднимает каждый dbt-тест как asset check в Dagster**.
Рукописная проверка была, таким образом, второй, дрейфующей копией правила, которое уже живёт
в SSoT.

## Решение

**Никогда не реализовывать в оркестраторе то, что умеет движок трансформаций.** Качество данных
выражается один раз — как проверки `spec/`, компилируемые в тесты dbt/SQLMesh, — а оркестратор
лишь *показывает* результаты. Конкретно:

- DQ-утверждение принадлежит `spec/sql/*` (`checks:`), а не Dagster-`asset_check` или Prefect-задаче.
- Автомаппинг `dagster-dbt` dbt-тестов → asset checks — санкционированный способ появления DQ
  в Dagster UI. Никаких рукописных зеркал.
- Оркестратор-нативные проверки резервируются строго для того, что движок действительно не может
  выразить (например, межсистемная свежесть, SLA времени выполнения), с пометкой *почему* в самой
  проверке.
- Словарь проверок никогда не должен падать молча. Громкие ворота — `to_sqlmesh` (ODTS §5),
  который проходит по тому же spec и отклоняет неизвестные имена проверок; `to_dbt` затем может
  пропустить проверку, не проецируемую для его целевого флейвора (например, пакетные тесты при
  `with_packages=False`), потому что словарь уже был провалидирован.

Это оркестрационное следствие правила AGENTS.md «экспериментальные движки *потребляют*
`spec/`, никогда его не дублируют» и правила SSoT (ADR-0005).

## Последствия

- **+** Один источник истины для DQ; нет дрейфа; переносимость между движками (тот же `spec/`
  управляет SQLMesh и dbt). Меньше кастомных Dagster-объектов на поддержку.
- **+** Исправлен латентный баг, вскрытый аудитом: карта проверок компилятора знала только
  `not_null`/`unique`, поэтому `non_negative` на `popularity_score` компилировался в **ничто**.
  Теперь `non_negative` → `dbt_utils.accepted_range(min_value=0)`, а словарь громко гейтится
  fail-loud в `to_sqlmesh`.
- **−** Видимость DQ в Dagster теперь зависит от того, что `dbt build` был запущен (dbt-тесты
  должны материализоваться как asset checks); чистый запуск по выборке ассетов, пропускающий dbt,
  их не покажет. Приемлемо — DQ есть свойство сборки, а не оркестрации.
- Утверждение о числе строк FS, которое также делала удалённая проверка, сохранено как финальные
  ворота в `experimental/orchestration/dagster_ogip/e2e/run_combo.sh`; тест таблицы на непустоту
  с тех пор приземлился в spec (`checks: [{name: not_empty}]` на `fs.market_features` →
  `dbt_expectations.expect_table_row_count_to_be_between`).

## Верификация

`dg check defs` чист; комбо-e2e зелёный — `dbt build` запускает 10 data-тестов (вкл.
`not_null_market_features_popularity_score` и `dbt_utils_accepted_range_…`), и лог запуска
показывает, что каждый из них оценён как `ASSET_CHECK_EVALUATION` на `fs/market_features`.
