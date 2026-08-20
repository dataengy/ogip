<!-- ru-translation-of: docs/superpowers/plans/2026-07-24-reroot-dbt-bruin-primary-candidates.md sha:70bf86e02193 -->
<!-- Автоперевод. Источник — docs/superpowers/plans/2026-07-24-reroot-dbt-bruin-primary-candidates.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [2026-07-24-reroot-dbt-bruin-primary-candidates.md](2026-07-24-reroot-dbt-bruin-primary-candidates.md)

# Re-root: prefect+dbt и prefect+Bruin как первичные кандидаты — план реализации

> **Для агентных исполнителей:** ОБЯЗАТЕЛЬНЫЙ САБ-СКИЛЛ: используйте superpowers:subagent-driven-development (рекомендуется) или superpowers:executing-plans, чтобы выполнять этот план задача за задачей. Шаги используют синтаксис чекбоксов (`- [ ]`) для трекинга.

**Цель:** Сделать **prefect+dbt** и **prefect+Bruin** двумя первичными, production-grade кандидатами сравнения; перенести все остальные движковые сетапы (sqlmesh, plain_sql, opendbt, sqlmesh_dbt, dagster) в experimental/R&D — вне дефолтного пути `make`/пайплайна.

**Архитектура:** OGIP авторит трансформы один раз в `spec/sql` (формат `@bruin`, ODTS — без YADTS). Сегодня spec-компилятор рендерит это в движковые проекты, а SQLMesh — жёстко зашитый продакшн-дефолт. Этот re-root инвертирует картину: dbt и Bruin становятся двумя ко-первичными рантаймами на дефолтном пути, прогоняемыми `make`/CI; остальные становятся сетапами сравнения под `experimental/`. Поскольку dbt становится первичным, комбо-путь dbt/Dagster (#38) и dbt-нативный DQ (#34) становятся фундаментальными, а не опциональными.

**Технологический стек:** Python 3.13 (uv, ruff, pyright-strict, pytest), DuckDB, dbt-core + dbt-duckdb, Bruin, Prefect 3.7, SQLGlot (компилятор), SQLMesh (теперь experimental).

## Глобальные ограничения

- **Нейминг ODTS решён: `ODTS`, без `YADTS`** (ADR-0018). Не возвращайте вариант YADTS.
- **`spec/` остаётся SSoT и не привязан к движку** — авторится в `@bruin` SQL; движковые проекты ГЕНЕРИРУЮТСЯ, никогда не форкаются вручную. Этот re-root не меняет формат авторинга; он меняет, какие сгенерированные движки первичны.
- **`spec/ODTS/examples/` — замороженный нормативный набор из 6 файлов** — `test_standard_packages.py` ассертит `==6` + побайтовую идентичность тел. НЕ добавляйте и не переформатируйте тела примеров.
- **Два ко-первичных, один технический дефолт для `make run`:** выбрать **prefect-dbt** как `default: true` (единственный дефолт, который нужен голому `make run`); **prefect-bruin** — ко-первичный и гейтится наравне. Оба ДОЛЖНЫ быть зелёными в `make check`.
- **Планка качества без изменений:** Ruff чистый, Pyright strict — 0 ошибок, pytest зелёный. Домашний алиас `log`. Каждая новая/изменённая директория сохраняет свой `README.md`. Архитектурное изменение ⇒ ADR.
- **Изолированный worktree + PR.** `dev` живёт под параллельными сессиями; делайте весь re-root в worktree и приземляйте через PR. Никогда не делайте force-push в `dev`/`main`.
- **Предусловия перед Task 1:** PR #29 смержен (он конфликтует по `pipelines/flows/main.py` + `pipelines/_shared/steps.py`, которые этот план перемещает), и линт `dev` зелёный (через #29). Ответвляйте worktree от `dev` после #29.
- Каждый коммит заканчивается `Refs: #40` (или конкретным под-issue #38/#39) + `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## Структура файлов

**Перемещено (git mv, с сохранением истории):**
- `pipelines/{sqlmesh,plain_sql,opendbt,sqlmesh_dbt,dagster}/` → `experimental/pipelines/{...}/` — пять пониженных подпроектов.
- `pipelines/{dbt,bruin}/` — ОСТАЮТСЯ (два первичных).
- `pipelines/_shared/` — ОСТАЁТСЯ (общая библиотека шагов; импортируется и первичными, и experimental-подпроектами).

**Изменено:**
- `pipelines/_shared/engines.py` — значения `ENGINE_FLOWS` перенацелены для перемещённых движков (`experimental.pipelines.<e>.flow`).
- `pipelines/_shared/steps.py::build_warehouse` — дефолтная ветка становится dbt; ветка sqlmesh по-прежнему достижима для experimental-сетапа.
- `src/ogip/spec_compile/__init__.py` + `to_dbt.py`/`to_bruin.py`/`to_sqlmesh.py` — dbt/bruin становятся дефолтными целями компиляции; расширить check-проекцию под dbt-нативные проверки из #34.
- `config/config.yml` — `run_profiles`: перенести `default: true` на `prefect-dbt`; пометить пятёрку как `experimental: true`.
- `.ai/AGENTS.md` — переписать жёсткие правила 1–2, раздел про production path и раздел run-профилей.
- `Makefile` — `run` → dbt; добавить `run-bruin` как ко-первичный; перенести таргеты sqlmesh/opendbt/etc в группу `experimental-*`.
- `src/scripts/run-profile.py` — без изменения логики (читает `ENGINE_FLOWS`); проверить, что он резолвит перемещённые модули.
- Тесты: `src/tests/unit/test_engine_projects_cover_spec.py`, `test_prefect_subprojects.py`, `src/tests/e2e/test_all_setups.py`.
- Снапшоты: `transform/dbt/`, `transform/bruin/` остаются закоммиченными + под дрифт-гардом; `transform/sqlmesh/models/` остаётся в gitignore.

**Создано:**
- `experimental/pipelines/README.md` — что здесь живёт и почему (сетапы сравнения, вне дефолтного пути).
- `docs/adr/ADR-0020-dbt-bruin-primary-candidates.md`.
- `src/scripts/preflight-clean-ground.sh` — разведка перед реструктуризацией (Task 9).
- `src/scripts/gh-merge-as.sh` — обёртка switch→merge→restore (Task 9).

---

## Task 1: Компилятор — dbt и Bruin как дефолтные цели; принять dbt-нативный DQ (#34)

**Файлы:**
- Изменить: `src/ogip/spec_compile/__init__.py`, `src/ogip/spec_compile/to_dbt.py`, `src/ogip/spec_compile/to_bruin.py`, `src/ogip/spec_compile/to_sqlmesh.py`
- Тест: `src/tests/unit/test_spec_compile_dq.py` (расширить), `src/tests/unit/test_reroot_default_targets.py` (создать)

**Интерфейсы:**
- Потребляет: существующие `compile_to_dbt(spec_sql, out)`, `compile_to_bruin(...)`, `compile_to_sqlmesh(...)` и заголовок `@bruin` в `Asset.meta` (сохраняет `columns[].checks`, верхнеуровневые `checks`, а теперь и `custom_checks`/`unit_tests`).
- Производит: `DEFAULT_ENGINES = ("dbt", "bruin")`; dbt-проекция эмитит `relationships`/`accepted_range`/`custom_checks` как dbt-тесты и `unit_tests` как dbt unit tests; sqlmesh-проекция терпит (игнорирует с залогированным скипом) dbt-only виды проверок, вместо того чтобы кидать `SqlSpecError`.

- [ ] **Шаг 1: Написать падающий тест** — dbt-нативные проверки проецируются в dbt-тесты и больше не роняют компиляцию sqlmesh.

```python
# src/tests/unit/test_spec_compile_dq.py (add)
def test_dbt_native_checks_project_to_dbt_tests(tmp_path):
    from ogip.spec_compile import compile_to_dbt
    # market_features carries relationships + custom_checks + unit_tests (from #34)
    proj = compile_to_dbt(SPEC_SQL, tmp_path)
    schema = (tmp_path / "models" / "fs" / "market_features.yml").read_text()
    assert "relationships" in schema and "to: ref('game')" in schema
    # custom_checks → a singular test file; unit_tests → dbt unit_tests block
    assert (tmp_path / "tests" / "popularity_requires_ratings.sql").exists()
    assert "unit_tests:" in schema

def test_sqlmesh_ignores_dbt_only_checks_without_crashing(tmp_path):
    from ogip.spec_compile import compile_to_sqlmesh
    # relationships/custom_checks/unit_tests are dbt-only; sqlmesh must SKIP, not raise
    models = compile_to_sqlmesh(SPEC_SQL, tmp_path / "models")
    assert "fs.market_features" in models  # compiled, dbt-only checks skipped
```

- [ ] **Шаг 2: Запустить и убедиться, что падает** — `uv run pytest src/tests/unit/test_spec_compile_dq.py -k dbt_native -q` → FAIL (relationships не эмитится / sqlmesh кидает исключение).

- [ ] **Шаг 3: Реализовать** — в `to_dbt.py` замапить `relationships`→dbt-тест `relationships`, `accepted_range`→`dbt_utils.accepted_range` (или `accepted_values`), `custom_checks[]`→singular-тесты в файлах `.sql` под `tests/`, `unit_tests[]`→блок `unit_tests:` в schema-yml модели. В `to_sqlmesh.py` изменить ветку неизвестной проверки: SQLMesh-нативный набор по-прежнему мапится в audits; dbt-only набор (`relationships`, `not_empty`, `custom_checks`, `unit_tests`) скипается через `log.debug`, а не через `SqlSpecError`. В `to_bruin.py` они проходят нативно (Bruin читает `@bruin`-проверки напрямую). Установить `DEFAULT_ENGINES = ("dbt", "bruin")` в `__init__.py`.

- [ ] **Шаг 4: Запустить и убедиться, что проходит** — та же команда → PASS. Также `uv run pytest src/tests/unit -k "spec_compile or reroot" -q`.

- [ ] **Шаг 5: Коммит** — `feat(spec-compile): dbt/bruin default targets; route dbt-native DQ, sqlmesh skips it` · `Refs: #40`.

---

## Task 2: Починить комбо-путь dbt/Dagster (#38) — сборка с полным набором источников

**Файлы:**
- Изменить: `spec/sql/staging/stg_metacritic_games.sql`, `stg_psn_concepts.sql`, `stg_steamcharts_apps.sql` (устойчивость к источникам) ИЛИ шаг ingest в комбо-e2e-харнессе dbt.
- Тест: `src/tests/e2e/test_all_setups.py::test_combo_dbt_builds` (сделать зелёным ассерт комбо dbt/dagster)

**Интерфейсы:**
- Потребляет: конвенцию raw-приземления (`<system>__<table>`), demo-safe фикстурные скрейперы (metacritic/opencritic/psn включены по умолчанию).
- Производит: сборка dbt по пути dlt→dbt проходит, даже когда raw скрейпленных источников пуст — staging-модели скрейпленных источников резолвятся против **всегда существующих (возможно, пустых) raw-таблиц**, а нижестоящие core-модели (`critic_reception`/`console_pricing`/`traction`) выдают ноль строк, а не падают с ошибкой.

- [ ] **Шаг 1: Написать падающий тест** — комбо-путь dbt собирается до FS без `Table does not exist`.

```python
def test_combo_dbt_builds_with_scraped_sources_absent(tmp_path, monkeypatch):
    # dlt path lands only rawg; scraped-source raw is empty but MUST exist as a relation
    result = run_setup("dbt")  # build staging→core→fs via dbt
    assert result["fs.market_features"] >= 1        # rawg spine survives
    assert result["core.critic_reception"] == 0     # no metacritic match → zero rows, not error
```

- [ ] **Шаг 2: Запустить и убедиться, что падает** — воспроизводит из #38 ошибку `Catalog Error: Table with name stg_metacritic_games does not exist`.

- [ ] **Шаг 3: Реализовать** — гарантировать, что raw-таблицы скрейпленных источников **материализуются пустыми** на этапе ingest (demo-safe скрейперы уже работают от фикстур; сделать так, чтобы определения dbt `source()` указывали на raw-отношения, которые шаг ingest гарантированно создаёт даже при нуле строк). Тогда staging-модели собираются (пустыми), а core-фиче-модели проходят LEFT JOIN через бридж → ноль сматченных строк, без ошибки отсутствующей таблицы. Сохранить спайн rawg нетронутым, чтобы `fs.market_features` по-прежнему имел строки.

- [ ] **Шаг 4: Запустить и убедиться, что проходит** — `uv run pytest src/tests/e2e/test_all_setups.py -k "combo_dbt or dbt" -q` и, с `OGIP_E2E_ALL_ENGINES=1`, комбо-джоб dagster. Убедиться, что CI-джоб `combo-e2e`/`dagster-e2e` становится зелёным.

- [ ] **Шаг 5: Коммит** — `fix(dbt): combo path builds with empty scraped-source staging (no missing-table)` · `Closes: #38`.

---

## Task 3: Физически перенести пять пониженных подпроектов в experimental/

**Файлы:**
- Переместить: `pipelines/{sqlmesh,plain_sql,opendbt,sqlmesh_dbt,dagster}/` → `experimental/pipelines/{...}/`
- Изменить: `pipelines/_shared/engines.py`, `src/tests/unit/test_prefect_subprojects.py`
- Создать: `experimental/pipelines/README.md`

**Интерфейсы:**
- Потребляет: `ENGINE_FLOWS` (имя трансформа → путь модуля), `make_engine_flow`.
- Производит: `ENGINE_FLOWS = {"dbt": "pipelines.dbt.flow", "bruin": "pipelines.bruin.flow", "sqlmesh": "experimental.pipelines.sqlmesh.flow", "plain_sql": "experimental.pipelines.plain_sql.flow", "opendbt": "experimental.pipelines.opendbt.flow", "sqlmesh_dbt": "experimental.pipelines.sqlmesh_dbt.flow", "dagster": "experimental.pipelines.dagster.flow"}`.

- [ ] **Шаг 1: Написать падающий тест** — тест подпроектов ассертит новые локации.

```python
_PRIMARY = ["dbt", "bruin"]                                   # in pipelines/
_EXPERIMENTAL = ["sqlmesh", "plain_sql", "opendbt", "sqlmesh_dbt", "dagster"]  # in experimental/pipelines/
def test_primary_subprojects_are_on_the_default_path():
    for e in _PRIMARY:
        assert (Path("pipelines") / e / "flow.py").is_file()
def test_experimental_subprojects_are_moved_off_the_path():
    for e in _EXPERIMENTAL:
        assert (Path("experimental/pipelines") / e / "flow.py").is_file()
        assert not (Path("pipelines") / e).exists()
```

- [ ] **Шаг 2: Запустить и убедиться, что падает** — директории ещё не перемещены.

- [ ] **Шаг 3: Реализовать** — `git mv` каждой из пяти директорий в `experimental/pipelines/`; обновить импорты в их `flow.py`, если какие-то используют перемещённый относительный путь (они импортируют из `pipelines._shared`, который не меняется — проверить). Перенацелить `ENGINE_FLOWS`. Написать `experimental/pipelines/README.md` (сетапы сравнения; потребляют `spec/`; никогда не находятся на дефолтном пути `make`/пайплайна). Сохранить реэкспорт `pipelines/flows/main.py`, указывающий на ПЕРВИЧНЫЙ: `from pipelines.dbt.flow import flow as ingest_transform_publish`.

- [ ] **Шаг 4: Запустить и убедиться, что проходит** — `uv run pytest src/tests/unit/test_prefect_subprojects.py -q` + `make check`.

- [ ] **Шаг 5: Коммит** — `refactor(pipelines): move sqlmesh/plain_sql/opendbt/sqlmesh_dbt/dagster to experimental/` · `Refs: #40`.

---

## Task 4: Переключить конфиг + run-профили + дефолт Makefile на dbt (bruin — ко-первичный)

**Файлы:**
- Изменить: `config/config.yml` (`run_profiles`), `Makefile`, `pipelines/_shared/steps.py::build_warehouse`
- Тест: `src/tests/unit/test_run_profiles.py` (создать/расширить)

**Интерфейсы:**
- Потребляет: SSoT `run_profiles`, `build_warehouse(engine)`.
- Производит: `prefect-dbt: {default: true}`; `prefect-bruin` ко-первичный (без флага `experimental`); остальные пять несут `experimental: true`. Дефолтная ветка `build_warehouse` запускает dbt; ветка sqlmesh достижима только для experimental-сетапа.

- [ ] **Шаг 1: Написать падающий тест**

```python
def test_default_profile_is_prefect_dbt():
    profiles = get_settings_yaml()["run_profiles"]
    assert profiles["prefect-dbt"].get("default") is True
    assert profiles["prefect-sqlmesh"].get("experimental") is True
    assert "experimental" not in profiles["prefect-bruin"]   # co-primary
```

- [ ] **Шаг 2: Запустить и убедиться, что падает.**

- [ ] **Шаг 3: Реализовать** — отредактировать `config/config.yml`: убрать `default: true` у `prefect-sqlmesh`, добавить у `prefect-dbt`; пометить `prefect-sql`/`prefect-opendbt`/`prefect-sqlmesh-over-dbt`/`prefect-over-dagster`/`prefect-dagster-dlt-dbt`/`prefect-sqlmesh` флагом `experimental: true`. Makefile: `run` → `just run-profile prefect-dbt`; добавить `run-bruin`; перегруппировать пятёрку под комментариями `experimental-run-*`. В `build_warehouse` сделать dbt дефолтом и загейтить ветку sqlmesh за `engine == "sqlmesh"` (уже так) — но убедиться, что ДЕФОЛТНАЯ константа движка, используемая `main.py`/`make run`, — это dbt.

- [ ] **Шаг 4: Запустить и убедиться, что проходит** — `uv run pytest src/tests/unit/test_run_profiles.py -q` + `make check`.

- [ ] **Шаг 5: Коммит** — `feat(config): prefect-dbt is default; bruin co-primary; rest experimental` · `Refs: #40`.

---

## Task 5: Переписать жёсткие правила AGENTS.md + нарратив production path

**Файлы:**
- Изменить: `.ai/AGENTS.md`
- Создать: `docs/adr/ADR-0020-dbt-bruin-primary-candidates.md`

**Интерфейсы:** нет (документация) — но это SSoT, по которому судят остальные задачи, поэтому формулировки должны совпадать с кодом.

- [ ] **Шаг 1** — Переписать раздел «production path»: производственный путь теперь запускает **dbt** (и Bruin как ко-первичный кандидат сравнения), оба генерируются из `spec/`. Убрать «the **only** production transform engine is **SQLMesh**»; заменить на «два первичных кандидата — dbt и Bruin; SQLMesh, plain-SQL, opendbt, sqlmesh-over-dbt и Dagster-сетапы — движки сравнения/experimental под `experimental/`».
- [ ] **Шаг 2** — Обновить Hard rule 2 («default runtime engine is SQLMesh» → «default runtime engine is dbt; Bruin is the co-primary; spec authoring stays `@bruin`»). Обновить список «Run & orchestration profiles» (default = `prefect-dbt`).
- [ ] **Шаг 3** — Написать ADR-0020 (проверить, что это следующий свободный номер — последний был 0019; сделать grep, чтобы избежать коллизии с OGAP). Зафиксировать: решение, понижение движков, зависимости #38/#34, почему физический перенос, а не только метки (выбор пользователя), и что это отменяет формулировку эпохи ADR «SQLMesh is production».
- [ ] **Шаг 4** — `grep -rn "only production transform engine is\|default runtime engine is SQLMesh" .` не возвращает ничего устаревшего.
- [ ] **Шаг 5: Коммит** — `docs(agents): dbt+bruin are the primary candidates; sqlmesh → experimental (ADR-0020)` · `Refs: #40`.

---

## Task 6: Тесты — дрифт-гард + e2e первичных + исполнение DQ в гейте

**Файлы:**
- Изменить: `src/tests/unit/test_engine_projects_cover_spec.py`, `src/tests/e2e/test_all_setups.py`, `Makefile` (таргет `check`)

**Интерфейсы:**
- Производит: `make check` запускает реальный DQ двух первичных (dbt `build` запускает dbt-тесты, включая тесты из #34; Bruin `validate` читает нативные `@bruin`-проверки) — закрывая разрыв исполнения аудитов ДЛЯ ПЕРВИЧНЫХ (разрыв sqlmesh-audit-deselect, ogip-dq-projection-and-gate-gap, остаётся только у теперь-experimental sqlmesh).

- [ ] **Шаг 1** — Расширить дрифт-гард: закоммиченные снапшоты `transform/dbt/` и `transform/bruin/` должны покрывать все spec-модели (уже покрывают); перегенерация через `uv run python -m ogip.spec_compile all`. Снапшот sqlmesh остаётся в gitignore + под гардом через прямой вызов компиляции.
- [ ] **Шаг 2** — В `test_all_setups.py` сделать так, чтобы base-setup e2e **dbt и bruin** выполнялись в ДЕФОЛТНОЙ выборке (не за `OGIP_E2E_ALL_ENGINES=1`); переместить sqlmesh/opendbt/sqlmesh_dbt/dagster за флаг.
- [ ] **Шаг 3** — `make check`: убедиться, что e2e dbt+bruin (которое исполняет их DQ) НЕ деселектится — это тот самый паритет гейта, который вариант «только метки» пропустил бы. Тяжёлые experimental-движки оставить деселекченными.
- [ ] **Шаг 4** — `make check` зелёный; `OGIP_E2E_ALL_ENGINES=1 uv run pytest src/tests/e2e -q` зелёный.
- [ ] **Шаг 5: Коммит** — `test(reroot): dbt+bruin e2e+DQ run in the gate; experimental engines behind the flag` · `Refs: #40`.

---

## Task 7: Перегенерировать снапшоты + пройтись по докам

- [ ] **Шаг 1** — `uv run python -m ogip.spec_compile all`; закоммитить перегенерированные `transform/dbt/`, `transform/bruin/`.
- [ ] **Шаг 2** — Обновить `pipelines/README.md`, `transform/README.md`, `README.md`, `config/README.md` под новый дефолт; каждая перемещённая директория сохраняет/получает `README.md`.
- [ ] **Шаг 3** — `grep -rn "prefect-sqlmesh (default\|production).*SQLMesh"` по докам → ничего устаревшего.
- [ ] **Шаг 4: Коммит** — `docs(reroot): sweep READMEs + regenerate dbt/bruin snapshots` · `Refs: #40`.

---

## Task 8: Уплотнить историю мониторинга/DQ ODOS для первичных (опционально, если в скоупе)

Направить мониторы freshness/row-count (`spec/dq/policy.yml`) на первичный dbt/bruin warehouse в `dq/run.py` (по-прежнему исполнение Фазы 4 — оставить как load+report, если пользователь не втягивает исполнение в этот слайс). Пропустить, если пользователь хочет оставить re-root механическим.

---

## Task 9: Материализовать pre-flight-скрипты (в репозитории, по кодовым стандартам)

**Файлы:**
- Создать: `src/scripts/preflight-clean-ground.sh`, `src/scripts/gh-merge-as.sh`
- Изменить: `Justfile` (passthrough-рецепты), `config/config.yml` (все скаляры: хост `github.com`, основная ветка `dev`)

- [ ] **Шаг 1** — `preflight-clean-ground.sh`: разведка, которая нужна предусловиям этого плана — таблица worktree (dirty/ahead-behind/merged), открытые PR + mergeable + сводка CI, детект устаревших локов + дубликатов по patch-id, вердикт `clean|not-clean + blockers`. Только чтение. Скаляры (ветка, хост) — из `config/config.yml`.
- [ ] **Шаг 2** — `gh-merge-as.sh <pr>`: `gh auth switch -u dataengy` → `gh pr merge` → восстановить прежний аккаунт; отказывается, если действие гейтится классификатором (печатает ручную инструкцию). Кодирует [[ogip-gh-merge-account-and-classifier]].
- [ ] **Шаг 3** — Вписать оба в `Justfile` (рецепты `preflight`, `merge-as`); `shellcheck -S error` чистый; добавить в `bash-lint`.
- [ ] **Шаг 4: Коммит** — `feat(scripts): preflight-clean-ground + gh-merge-as (in-repo, code-standard)` · `Refs: #40`.

> **Заметка о каталожных скиллах:** `/land-conflicting-pr` и хуки ruff-parity / combo-e2e (#39/#38) предложены как скиллы/хуки ОБЩЕГО КАТАЛОГА, создаваемые через `/create-skill` + `/save-all-deterministic-for-skill-as-scripts` (никогда вручную). Они вне скоупа этого внутрирепозиторного плана; поднимите их отдельно, когда каталожный тулинг будет доступен в сессии.

---

## Самопроверка

- **Покрытие спеки:** понижение движков (T3/T4), нарратив (T5), первичность компилятора + DQ из #34 (T1), фикс #38 (T2), паритет гейта (T6), снапшоты/доки (T7), скрипты (T9), #39 обработан в ADR из T5 + заметке T9. ✔
- **Порядок:** T1→T2 (компилятор + зелёный dbt-путь) ПЕРЕД T3/T4 (переносом), чтобы первичные были доказанно зелёными до того, как станут единственным дефолтом. T5/T6/T7 — после. ✔
- **Зависимость от #29:** указана в Глобальных ограничениях (он перемещает `pipelines/_shared/steps.py` + `main.py`). ✔
- **Консистентность типов:** ключи `ENGINE_FLOWS` идентичны по всему T3; `DEFAULT_ENGINES=("dbt","bruin")` используется в T1/T4/T6. ✔
- **Риск:** самый большой радиус поражения; изоляция worktree+PR + последовательность «T1/T2 до переноса» его сдерживают. ADR-0020 фиксирует отмену жёсткого правила «SQLMesh is production».

## Передача на исполнение

План сохранён. Два варианта исполнения: **(1) Subagent-Driven (рекомендуется)** — свежий сабагент на задачу + двухступенчатое ревью; **(2) Inline** — executing-plans с чекпоинтами. Исполнение начинается, как только **PR #29 смержен** и worktree ответвлён от `dev` после #29.

---

## Журнал исполнения / состояние для резюма (2026-07-27)

Ветка **`lane/reroot-dbt-bruin-primary`** (запушена). PR #29 смержен (`dev@3b1d4b9`); ветка — пост-#29.

**СДЕЛАНО + запушено:**
- **Task 1** — компилятор в обе стороны. `to_sqlmesh` терпит dbt-нативные проверки через явный allowlist `_DBT_ONLY_CHECKS={relationships,not_empty}` (опечатка по-прежнему падает громко) + форму `accepted_range` `value:{min,max}` (`bfb3e54`). `to_dbt` эмитит весь словарь проверок как настоящие dbt-тесты; **без-пакетные разновидности (opendbt/sqlmesh_dbt, `with_packages=False`) получают только ВСТРОЕННЫЕ в dbt-core тесты** — `dbt_utils`/`dbt_expectations` там выброшены (`9d4ee74` + `b985d41`).
- **Task 2 / #38** — комбо-путь dagster+dbt: таска `ingest.scraped` приземляет raw скрейпленных источников (половина на стороне Prefect); вшита в `flow_dagster` (тоже реальный прод-баг) + `run_combo.sh` (через основной venv) + `dagster-e2e.yml` (синкает основной env). Проверено тяжёлым e2e: dbt ✓, opendbt ✓ (`b985d41`).
- **Task 3** — пять движков перенесены `git mv`→ `experimental/pipelines/`; `ENGINE_FLOWS` + `main.py`(→dbt) + импорт в e2e + entrypoints перемещённых `prefect.yaml` перенацелены (`df82dc8`).

**ОСТАЛОСЬ = Задачи 4–9** (этот документ, выше): 4 — дефолт конфига→dbt + Makefile · 5 — переписывание жёстких правил AGENTS.md + ADR-0020 · 6 — e2e/DQ dbt+bruin в гейте, experimental за флагом · 7 — проход по докам (**уже устарело**: `pipelines/README.md:21`, `spec/ODOS/IMPLEMENTATION.md:167`, проза ADR-0019) · 9 — внутрирепозиторные скрипты.

**Открытые issue, вобранные сюда:** #38 исправлен · #42 (тяжёлое e2e sqlmesh_dbt сломано ранее, raw external-table Catalog Error — доказано, что не моё) · #39 (ruff nested-config silent gate) · #40 (этот re-root).

**ОПАСНОСТЬ — движуха параллельной сессии.** Сосед вживую редактирует `spec/ODTS/` в этом общем чекауте (его незавершённый фикс fixture-дрифта роняет `test_standard_packages.py::test_odts_fixture_checks_match_spec_sql` — не связано с re-root, который не трогает ни одного файла в `spec/`). **Делайте Задачи 4–6 в изолированном worktree** от `origin/lane/reroot-dbt-bruin-primary`, чтобы уйти от этого. Стейджите только файлы re-root; никогда не коммитьте соседские `spec/ODTS`, `.gitignore`, `.ai/CONTEXT.man.md` или `.cache/`.

**Побочная незакоммиченная работа (не re-root):** `.ai/AI-glossary.en.md` (+5 терминов аудита, держится вне re-root-коммитов по правилу no-auto-commit для глоссария). Создан и задеплоен новый скилл: `/audit-feature-implementation-and-integration` (`de/local-dev/`).

**Проверка каждой задачи:** `make check` (ruff+pyright+pytest) И — для любого изменения DQ/модели/движка — деселектнутое e2e (`test_all_setups.py::test_base_setup_builds_and_produces_ml -k <engine>`, тяжёлое за `OGIP_E2E_ALL_ENGINES=1`), потому что `make check` деселектит e2e.
