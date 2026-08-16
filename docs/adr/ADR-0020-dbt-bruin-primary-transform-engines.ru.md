<!-- ru-translation-of: docs/adr/ADR-0020-dbt-bruin-primary-transform-engines.md sha:e687ef7c98a9 -->
<!-- Автоперевод. Источник — docs/adr/ADR-0020-dbt-bruin-primary-transform-engines.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0020-dbt-bruin-primary-transform-engines.md](ADR-0020-dbt-bruin-primary-transform-engines.md)

# ADR-0020 — dbt (primary) + Bruin (co-primary) как движки трансформаций; SQLMesh становится сравнительным сетапом

- **Статус:** Accepted
- **Дата:** 2026-07-30
- **Связано с:** решение D5 в PLAN · [ADR-0004](ADR-0004-sqlmesh-default-transform-engine.md) ·
  [ADR-0005](ADR-0005-spec-ssot-bruin-odcs-compiler.md) · план re-root
  ([docs/superpowers/plans/2026-07-24-reroot-dbt-bruin-primary-candidates.md](../superpowers/plans/2026-07-24-reroot-dbt-bruin-primary-candidates.md),
  [#40](https://github.com/dataengy/ogip/issues/40))

## Контекст

D5/ADR-0004 сделали SQLMesh движком трансформаций по умолчанию, а dbt/Bruin/plain-SQL —
генерируемыми сравнительными проектами. С тех пор баланс свидетельств сместился (док кандидатов
re-root, #40):

- Каждый проект движка **генерируется из `spec/`** (ADR-0005), поэтому «primary» — это флаг
  компилятора и обвязки, а не переписывание: цена понижения/повышения мала по построению.
- **dbt** — движок, который аудитория витрины читает свободно, и самые богатые интеграции
  движков в репозитории уже живут на dbt-пути (пакеты dbt-hub, project-evaluator, dbt-нативные
  DQ-тесты, Dagster-компонент `DbtProjectComponent`, SQLMesh-over-dbt).
- **Bruin** — путь без трансляции: `spec/sql` *и есть* формат Bruin/`@odts`, и Bruin исполняет
  его нативно на DuckDB — наличие одного движка, потребляющего spec без шага рендеринга,
  держит компилятор честным.
- Задачи re-root 1–3 уже приземлили механику: dbt+bruin — это `DEFAULT_ENGINES` в компиляторе,
  пять пониженных Prefect-подпроектов переехали в `experimental/pipelines/`.

## Решение

Мы делаем **dbt основным (primary)**, а **Bruin со-основным (co-primary)** движками
трансформаций. Профиль запуска по умолчанию — `prefect-dbt` (`make run` → `run-dbt`);
`prefect-bruin` и комбо `prefect-over-dagster` (Prefect + dbt-под-Dagster) — два других
первоклассных, гарантированных для демо сетапа. Профили SQLMesh, plain-SQL, OpenDBT и
SQLMesh-over-dbt несут `experimental: true` в `config/config.yml`, печатают баннер EXPERIMENTAL
при запуске, а их e2e спрятан за `OGIP_E2E_ALL_ENGINES=1`. Ворота по умолчанию (`make check`,
CI e2e) прогоняют dbt + Bruin.

## Последствия

- Демо-история читаема для своей аудитории (dbt) и при этом доказывает spec-first-дизайн
  (Bruin исполняет spec нативно; оба перегенерируются, никогда не форкаются вручную).
- Ворота становятся дешевле и точнее: 2 primary-движка вместо 5 полуприкрытых воротами.
- DQ-проекция из ADR-0019 продолжает работать — `columns[].checks` проецируются в dbt-тесты на
  primary-пути; рендеринг SQLMesh-аудитов по-прежнему прогоняется только под флагом полной матрицы.
- Доки/тесты, несущие утверждение «SQLMesh — primary», должны быть перевёрнуты в том же наборе
  изменений (жёсткие правила AGENTS.md, `config/config.yml`, `Makefile`, `test_wiring`,
  `test_all_setups`, README-файлы — re-root T4–T7).
- ADR-0004 остаётся Accepted как история; этот ADR уточняет его пункт о «движке по умолчанию»
  так же, как ADR-0016 уточняет пункт о формате в ADR-0005.

## Рассмотренные альтернативы

- **Оставить SQLMesh primary** — отклонено: читаемость для аудитории и ценность демонстрации
  экосистемы лежат на dbt-пути; SQLMesh остаётся поддерживаемым сравнительным сетапом,
  а не удаляется.
- **Только Bruin как primary** — отклонено: теряется демонстрация индустриального стандарта;
  Bruin в одиночку недоиспользует машинерию генерируемых проектов, ради показа которой
  компилятор и существует.
- **dbt под оркестрацией Dagster как вариант по умолчанию** — отклонено: Dagster остаётся
  альтернативной витриной оркестрации (шов `prefect-over-dagster` + автономный `dagster_ogip`),
  Prefect остаётся оркестратором платформы (D3/D9).
