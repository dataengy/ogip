<!-- ru-translation-of: docs/superpowers/plans/2026-07-24-reroot-dbt-bruin-primary-candidates.md sha:94a92c04470a -->
<!-- Автоперевод. Источник — docs/superpowers/plans/2026-07-24-reroot-dbt-bruin-primary-candidates.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [2026-07-24-reroot-dbt-bruin-primary-candidates.md](2026-07-24-reroot-dbt-bruin-primary-candidates.md)

# Re-root: план внедрения prefect+dbt и prefect+Bruin как основных кандидатов

> **Для агентных исполнителей:** ОБЯЗАТЕЛЬНЫЙ СУБ-СКИЛЛ: используйте superpowers:subagent-driven-development (рекомендуется) или superpowers:executing-plans для реализации этого плана задача за задачей. Шаги используют синтаксис чекбоксов (`- [ ]`) для отслеживания.

**Goal:** Сделать **prefect+dbt** и **prefect+Bruin** двумя основными, production-grade кандидатами для сравнения; переместить каждый другой setup движка (sqlmesh, plain_sql, opendbt, sqlmesh_dbt, dagster) в experimental/R&D — вне пути по умолчанию `make`/pipeline.

**Architecture:** OGIP авторит трансформации один раз в `spec/sql` (формат `@bruin`, ODTS — без YADTS). Сегодня spec-компилятор рендерит это в проекты движков, и SQLMesh — жёстко зашитый production-default. Этот re-root инвертирует картину: dbt и Bruin становятся двумя co-primary рантаймами на пути по умолчанию, прогоняемыми `make`/CI; остальные становятся setup-ами для сравнения под `experimental/`. Поскольку dbt становится основным, путь связки dbt/Dagster (#38) и dbt-native DQ (#34) становятся фундаментальными, а не опциональными.

**Tech Stack:** Python 3.13 (uv, ruff, pyright-strict, pytest), DuckDB, dbt-core + dbt-duckdb, Bruin, Prefect 3.7, SQLGlot (компилятор), SQLMesh (теперь экспериментальный).

## Глобальные ограничения

- **Именование ODTS зафиксировано: `ODTS`, без `YADTS`** (ADR-0018). Не вводить заново вариант YADTS.
- **`spec/` остаётся SSoT и движко-агностичной** — авторится в `@bruin` SQL; проекты движков ГЕНЕРИРУЮТСЯ, никогда не форкаются вручную. Этот re-root не меняет формат авторинга; он меняет, какие сгенерированные движки являются основными.
- **`spec/ODTS/examples/` — замороженный нормативный набор из 6 файлов** — `test_standard_packages.py` утверждает `==6` + побайтовую идентичность тел. НЕ добавляйте и не переформатируйте тела примеров.
- **Два co-primary, один технический default для `make run`:** выбираем **prefect-dbt** как `default: true` (единственный дефолт, который нужен голому `make run`); **prefect-bruin** — co-primary и гейтится наравне. Оба ДОЛЖНЫ быть зелёными в `make check`.
- **Планка качества без изменений:** Ruff чист, Pyright strict 0 ошибок, pytest зелёный. Домашний алиас `log`. Каждая новая/изменённая директория сохраняет свой `README.md`. Архитектурное изменение ⇒ ADR.
- **Изолированный worktree + PR.** `dev` активна под параллельными сессиями; делайте весь re-root в worktree и приземляйте через PR. Никогда не делайте force-push `dev`/`main`.
- **Предусловия до Task 1:** PR #29 смёржен (он конфликтует по `pipelines/flows/main.py` + `pipelines/_shared/steps.py`, которые этот план перемещает), и линт `dev` зелёный (через #29). Ответвите worktree от `dev` после #29.
- Каждый коммит заканчивается на `Refs: #40` (или конкретный саб-issue #38/#39) + `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## Структура файлов

**Перемещено (git mv, с сохранением истории):**
- `pipelines/{sqlmesh,plain_sql,opendbt,sqlmesh_dbt,dagster}/` → `experimental/pipelines/{...}/` — пять понижённых саб-проектов.
- `pipelines/{dbt,bruin}/` — ОСТАЮТСЯ (два основных).
- `pipelines/_shared/` — ОСТАЁТСЯ (общая библиотека шагов; импортируется и основными, и экспериментальными саб-проектами).

**Изменено:**
- `pipelines/_shared/engines.py` — значения `ENGINE_FLOWS` перенаправлены для перемещённых движков (`experimental.pipelines.<e>.flow`).
- `pipelines/_shared/steps.py::build_warehouse` — ветка по умолчанию становится dbt; ветка sqlmesh остаётся достижимой для экспериментального setup-а.
- `src/ogip/spec_compile/__init__.py` + `to_dbt.py`/`to_bruin.py`/`to_sqlmesh.py` — dbt/bruin становятся compile-целями по умолчанию; расширяем check-проекцию под dbt-native проверки #34.
- `config/config.yml` — `run_profiles`: перенести `default: true` на `prefect-dbt`; переметить пять как `experimental: true`.
- `.ai/AGENTS.md` — переписать hard rules 1–2, секцию production-path и секцию run-profiles.
- `Makefile` — `run` → dbt; добавить `run-bruin` как co-primary; переместить цели sqlmesh/opendbt/etc в группу `experimental-*`.
- `src/scripts/run-profile.py` — без изменения логики (читает `ENGINE_FLOWS`); проверить, что он резолвит перемещённые модули.
- Тесты: `src/tests/unit/test_engine_projects_cover_spec.py`, `test_prefect_subprojects.py`, `src/tests/e2e/test_all_setups.py`.
- Снапшоты: `transform/dbt/`, `transform/bruin/` остаются закоммиченными + под drift-guard; `transform/sqlmesh/models/` остаётся в gitignore.

**Создано:**
- `experimental/pipelines/README.md` — что здесь живёт и почему (setup-ы для сравнения, вне пути по умолчанию).
- `docs/adr/ADR-0020-dbt-bruin-primary-candidates.md`.
- `src/scripts/preflight-clean-ground.sh` — пред-реструктуризационная разведка (Task 9).
- `src/scripts/gh-merge-as.sh` — обёртка switch→merge→restore (Task 9).

---

## Task 1: Компилятор — dbt & Bruin как цели по умолчанию; принять dbt-native DQ (#34)

**Files:**
- Modify: `src/ogip/spec_compile/__init__.py`, `src/ogip/spec_compile/to_dbt.py`, `src/ogip/spec_compile/to_bruin.py`, `src/ogip/spec_compile/to_sqlmesh.py`
- Test: `src/tests/unit/test_spec_compile_dq.py` (расширить), `src/tests/unit/test_reroot_default_targets.py` (создать)

**Interfaces:**
- Consumes: существующие `compile_to_dbt(spec_sql, out)`, `compile_to_bruin(...)`, `compile_to_sqlmesh(...)` и заголовок `@bruin` в `Asset.meta` (сохраняет `columns[].checks`, верхнеуровневые `checks` и теперь `custom_checks`/`unit_tests`).
- Produces: `DEFAULT_ENGINES = ("dbt", "bruin")`; dbt-проекция выдаёт `relationships`/`accepted_range`/`custom_checks` как dbt-тесты и `unit_tests` как dbt unit-тесты; sqlmesh-проекция терпит (игнорирует с логируемым skip) dbt-only типы проверок вместо возбуждения `SqlSpecError`.

- [ ] **Step 1: Написать падающий тест** — dbt-native проверки проецируются в dbt-тесты и больше не роняют компиляцию sqlmesh.

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

- [ ] **Step 2: Запустить и убедиться, что падает** — `uv run pytest src/tests/unit/test_spec_compile_dq.py -k dbt_native -q` → FAIL (relationships не выдаются / sqlmesh падает).

- [ ] **Step 3: Реализовать** — в `to_dbt.py` отобразить `relationships`→dbt-тест `relationships`, `accepted_range`→`dbt_utils.accepted_range` (или `accepted_values`), `custom_checks[]`→singular-тест `.sql`-файлы под `tests/`, `unit_tests[]`→блок `unit_tests:` в schema-yml модели. В `to_sqlmesh.py` изменить ветку неизвестной проверки: SQLMesh-native набор по-прежнему отображается в audits; dbt-only набор (`relationships`, `not_empty`, `custom_checks`, `unit_tests`) пропускается через `log.debug` вместо `SqlSpecError`. В `to_bruin.py` они проходят нативно (Bruin читает `@bruin`-проверки напрямую). Установить `DEFAULT_ENGINES = ("dbt", "bruin")` в `__init__.py`.

- [ ] **Step 4: Запустить и убедиться, что проходит** — та же команда → PASS. Также `uv run pytest src/tests/unit -k "spec_compile or reroot" -q`.

- [ ] **Step 5: Коммит** — `feat(spec-compile): dbt/bruin default targets; route dbt-native DQ, sqlmesh skips it` · `Refs: #40`.

---

## Task 2: Починить путь связки dbt/Dagster (#38) — сборка с полным набором источников

**Files:**
- Modify: `spec/sql/staging/stg_metacritic_games.sql`, `stg_psn_concepts.sql`, `stg_steamcharts_apps.sql` (устойчивость источников) ЛИБО шаг ingest в combo-e2e-харнессе dbt.
- Test: `src/tests/e2e/test_all_setups.py::test_combo_dbt_builds` (сделать combo dbt/dagster зелёным)

**Interfaces:**
- Consumes: конвенцию raw landing (`<system>__<table>`), demo-safe fixture-скраперы (metacritic/opencritic/psn включены по умолчанию).
- Produces: dbt-сборка по пути dlt→dbt успешна, даже когда raw скрапящего источника пуст — staging-модели скрапящих источников резолвятся против **всегда присутствующих (возможно пустых) raw-таблиц**, а нижестоящие core-модели (`critic_reception`/`console_pricing`/`traction`) выдают ноль строк, а не падают.

- [ ] **Step 1: Написать падающий тест** — combo dbt-путь собирается до FS без `Table does not exist`.

```python
def test_combo_dbt_builds_with_scraped_sources_absent(tmp_path, monkeypatch):
    # dlt path lands only rawg; scraped-source raw is empty but MUST exist as a relation
    result = run_setup("dbt")  # build staging→core→fs via dbt
    assert result["fs.market_features"] >= 1        # rawg spine survives
    assert result["core.critic_reception"] == 0     # no metacritic match → zero rows, not error
```

- [ ] **Step 2: Запустить и убедиться, что падает** — воспроизводит #38 `Catalog Error: Table with name stg_metacritic_games does not exist`.

- [ ] **Step 3: Реализовать** — обеспечить, чтобы raw-таблицы скрапящих источников **материализовались пустыми** на этапе ingest (demo-safe скраперы уже работают на fixture-ах; сделать так, чтобы определения dbt `source()` указывали на raw-отношения, которые шаг ingest гарантированно создаёт даже с нулём строк). Staging-модели тогда собираются (пустыми), а core feature-модели LEFT JOIN через bridge → ноль совпавших строк, без ошибки missing-table. Сохранить rawg-spine целым, чтобы у `fs.market_features` всё ещё были строки.

- [ ] **Step 4: Запустить и убедиться, что проходит** — `uv run pytest src/tests/e2e/test_all_setups.py -k "combo_dbt or dbt" -q` и, с `OGIP_E2E_ALL_ENGINES=1`, combo-джоб dagster. Подтвердить, что CI-джоб `combo-e2e`/`dagster-e2e` становится зелёным.

- [ ] **Step 5: Коммит** — `fix(dbt): combo path builds with empty scraped-source staging (no missing-table)` · `Closes: #38`.

---

## Task 3: Физически переместить пять понижённых саб-проектов в experimental/

**Files:**
- Move: `pipelines/{sqlmesh,plain_sql,opendbt,sqlmesh_dbt,dagster}/` → `experimental/pipelines/{...}/`
- Modify: `pipelines/_shared/engines.py`, `src/tests/unit/test_prefect_subprojects.py`
- Create: `experimental/pipelines/README.md`

**Interfaces:**
- Consumes: `ENGINE_FLOWS` (transform-имя → путь модуля), `make_engine_flow`.
- Produces: `ENGINE_FLOWS = {"dbt": "pipelines.dbt.flow", "bruin": "pipelines.bruin.flow", "sqlmesh": "experimental.pipelines.sqlmesh.flow", "plain_sql": "experimental.pipelines.plain_sql.flow", "opendbt": "experimental.pipelines.opendbt.flow", "sqlmesh_dbt": "experimental.pipelines.sqlmesh_dbt.flow", "dagster": "experimental.pipelines.dagster.flow"}`.

- [ ] **Step 1: Написать падающий тест** — тест саб-проектов утверждает новые расположения.

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

- [ ] **Step 2: Запустить и убедиться, что падает** — директории ещё не перемещены.

- [ ] **Step 3: Реализовать** — `git mv` каждой из пяти директорий в `experimental/pipelines/`; обновить их импорты в `flow.py`, если какие-то используют перемещённо-относительный путь (они импортируют из `pipelines._shared`, который не изменён — проверить). Перенаправить `ENGINE_FLOWS`. Написать `experimental/pipelines/README.md` (setup-ы для сравнения; потребляют `spec/`; никогда не на пути по умолчанию `make`/pipeline). Оставить re-export `pipelines/flows/main.py`, указывающий на PRIMARY: `from pipelines.dbt.flow import flow as ingest_transform_publish`.

- [ ] **Step 4: Запустить и убедиться, что проходит** — `uv run pytest src/tests/unit/test_prefect_subprojects.py -q` + `make check`.

- [ ] **Step 5: Коммит** — `refactor(pipelines): move sqlmesh/plain_sql/opendbt/sqlmesh_dbt/dagster to experimental/` · `Refs: #40`.

---

## Task 4: Переключить config + run-профили + Makefile-дефолт на dbt (bruin co-primary)

**Files:**
- Modify: `config/config.yml` (`run_profiles`), `Makefile`, `pipelines/_shared/steps.py::build_warehouse`
- Test: `src/tests/unit/test_run_profiles.py` (создать/расширить)

**Interfaces:**
- Consumes: `run_profiles` SSoT, `build_warehouse(engine)`.
- Produces: `prefect-dbt: {default: true}`; `prefect-bruin` co-primary (без флага `experimental`); остальные пять несут `experimental: true`. Ветка по умолчанию `build_warehouse` запускает dbt; ветка sqlmesh достижима только для экспериментального setup-а.

- [ ] **Step 1: Написать падающий тест**

```python
def test_default_profile_is_prefect_dbt():
    profiles = get_settings_yaml()["run_profiles"]
    assert profiles["prefect-dbt"].get("default") is True
    assert profiles["prefect-sqlmesh"].get("experimental") is True
    assert "experimental" not in profiles["prefect-bruin"]   # co-primary
```

- [ ] **Step 2: Запустить и убедиться, что падает.**

- [ ] **Step 3: Реализовать** — отредактировать `config/config.yml`: убрать `default: true` из `prefect-sqlmesh`, добавить в `prefect-dbt`; пометить `prefect-sql`/`prefect-opendbt`/`prefect-sqlmesh-over-dbt`/`prefect-over-dagster`/`prefect-dagster-dlt-dbt`/`prefect-sqlmesh` с `experimental: true`. Makefile: `run` → `just run-profile prefect-dbt`; добавить `run-bruin`; перегруппировать пять под комментарии `experimental-run-*`. В `build_warehouse` сделать dbt дефолтом и загейтить ветку sqlmesh за `engine == "sqlmesh"` (уже так) — но убедиться, что константа DEFAULT-движка, используемая `main.py`/`make run`, — это dbt.

- [ ] **Step 4: Запустить и убедиться, что проходит** — `uv run pytest src/tests/unit/test_run_profiles.py -q` + `make check`.

- [ ] **Step 5: Коммит** — `feat(config): prefect-dbt is default; bruin co-primary; rest experimental` · `Refs: #40`.

---

## Task 5: Переписать hard rules AGENTS.md + нарратив production-path

**Files:**
- Modify: `.ai/AGENTS.md`
- Create: `docs/adr/ADR-0020-dbt-bruin-primary-candidates.md`

**Interfaces:** нет (документы) — но это SSoT, по которому судят остальные задачи, поэтому формулировки должны совпадать с кодом.

- [ ] **Step 1** — Переписать секцию «production path»: production-путь теперь запускает **dbt** (и Bruin как co-primary кандидат для сравнения), оба генерируются из `spec/`. Убрать «the **only** production transform engine is **SQLMesh**»; заменить на «два основных кандидата — dbt и Bruin; SQLMesh, plain-SQL, opendbt, sqlmesh-over-dbt и setup-ы Dagster — движки для сравнения/эксперименты под `experimental/`.»
- [ ] **Step 2** — Обновить Hard rule 2 («default runtime engine is SQLMesh» → «default runtime engine is dbt; Bruin is the co-primary; авторинг spec остаётся `@bruin`»). Обновить список «Run & orchestration profiles» (default = `prefect-dbt`).
- [ ] **Step 3** — Написать ADR-0020 (проверить, что это следующий свободный номер — последний был 0019; сделать grep во избежание коллизии с OGAP). Зафиксировать: решение, понижение, зависимости #38/#34, почему физическое перемещение, а не только метки (выбор пользователя), и что это разворачивает формулировку ADR-эпохи «SQLMesh — это production».
- [ ] **Step 4** — `grep -rn "only production transform engine is\|default runtime engine is SQLMesh" .` не возвращает ничего устаревшего.
- [ ] **Step 5: Коммит** — `docs(agents): dbt+bruin are the primary candidates; sqlmesh → experimental (ADR-0020)` · `Refs: #40`.

---

## Task 6: Тесты — drift guard + primary e2e + выполнение DQ в гейте

**Files:**
- Modify: `src/tests/unit/test_engine_projects_cover_spec.py`, `src/tests/e2e/test_all_setups.py`, `Makefile` (цель `check`)

**Interfaces:**
- Produces: `make check` запускает реальный DQ двух основных (dbt `build` прогоняет dbt-тесты вкл. #34; Bruin `validate` читает нативные `@bruin`-проверки) — закрывая пробел выполнения audits ДЛЯ ОСНОВНЫХ (пробел sqlmesh-audit-deselect, ogip-dq-projection-and-gate-gap, остаётся только для теперь-экспериментального sqlmesh).

- [ ] **Step 1** — Расширить drift-guard: закоммиченные снапшоты `transform/dbt/` и `transform/bruin/` должны покрывать все spec-модели (уже покрывают); регенерировать через `uv run python -m ogip.spec_compile all`. Снапшот sqlmesh остаётся в gitignore + под guard-ом через прямой вызов compile.
- [ ] **Step 2** — В `test_all_setups.py` сделать так, чтобы base-setup e2e **dbt и bruin** выполнялись в выборке ПО УМОЛЧАНИЮ (не за `OGIP_E2E_ALL_ENGINES=1`); переместить sqlmesh/opendbt/sqlmesh_dbt/dagster за флаг.
- [ ] **Step 3** — `make check`: обеспечить, чтобы e2e dbt+bruin (который выполняет их DQ) НЕ отсеивался — это паритет гейта, который вариант «только метки» пропустил бы. Оставить тяжёлые экспериментальные движки отсеянными.
- [ ] **Step 4** — `make check` зелёный; `OGIP_E2E_ALL_ENGINES=1 uv run pytest src/tests/e2e -q` зелёный.
- [ ] **Step 5: Коммит** — `test(reroot): dbt+bruin e2e+DQ run in the gate; experimental engines behind the flag` · `Refs: #40`.

---

## Task 7: Регенерировать снапшоты + сверка документов

- [ ] **Step 1** — `uv run python -m ogip.spec_compile all`; закоммитить регенерированные `transform/dbt/`, `transform/bruin/`.
- [ ] **Step 2** — Обновить `pipelines/README.md`, `transform/README.md`, `README.md`, `config/README.md` под новый дефолт; каждая перемещённая директория сохраняет/получает `README.md`.
- [ ] **Step 3** — `grep -rn "prefect-sqlmesh (default\|production).*SQLMesh"` в документах → ничего устаревшего.
- [ ] **Step 4: Коммит** — `docs(reroot): sweep READMEs + regenerate dbt/bruin snapshots` · `Refs: #40`.

---

## Task 8: Уплотнить историю мониторинга/DQ ODOS для основных (опционально, если в scope)

Направить мониторы свежести/числа строк (`spec/dq/policy.yml`) на выполнение против основного хранилища dbt/bruin в `dq/run.py` (по-прежнему выполнение Phase-4 — держать как load+report, если пользователь не втянет выполнение в этот срез). Пропустить, если пользователь хочет держать re-root механическим.

---

## Task 9: Материализовать pre-flight скрипты (in-repo, по код-стандартам)

**Files:**
- Create: `src/scripts/preflight-clean-ground.sh`, `src/scripts/gh-merge-as.sh`
- Modify: `Justfile` (passthrough-рецепты), `config/config.yml` (любые скаляры: хост `github.com`, основная ветка `dev`)

- [ ] **Step 1** — `preflight-clean-ground.sh`: разведка, которую требуют предусловия этого плана — таблица worktree (dirty/ahead-behind/merged), открытые PR + mergeable + свод CI, детекция stale-lock + patch-id-дубликатов, вердикт `clean|not-clean + blockers`. Только чтение. Скаляры (branch, host) из `config/config.yml`.
- [ ] **Step 2** — `gh-merge-as.sh <pr>`: `gh auth switch -u dataengy` → `gh pr merge` → восстановить прежний аккаунт; отказывается, если действие загейчено классификатором (печатает ручную инструкцию). Кодирует [[ogip-gh-merge-account-and-classifier]].
- [ ] **Step 3** — Подключить оба в `Justfile` (рецепты `preflight`, `merge-as`); `shellcheck -S error` чист; добавить в `bash-lint`.
- [ ] **Step 4: Коммит** — `feat(scripts): preflight-clean-ground + gh-merge-as (in-repo, code-standard)` · `Refs: #40`.

> **Заметка про каталог скиллов:** `/land-conflicting-pr` и хуки ruff-parity / combo-e2e (#39/#38) предлагаются как скиллы/хуки SHARED-CATALOG, собираемые через `/create-skill` + `/save-all-deterministic-for-skill-as-scripts` (никогда не вручную). Они вне scope этого in-repo плана; поднимите их отдельно, как только каталожная оснастка станет доступна в сессии.

---

## Само-ревью

- **Покрытие spec:** понижение (T3/T4), нарратив (T5), первичность компилятора + DQ #34 (T1), фикс #38 (T2), паритет гейта (T6), снапшоты/документы (T7), скрипты (T9), #39 обработан в ADR из T5 + заметке T9. ✔
- **Порядок:** T1→T2 (компилятор + dbt-путь зелёный) ДО T3/T4 (перемещение), чтобы основные были доказанно зелёными до того, как станут единственным дефолтом. T5/T6/T7 после. ✔
- **Зависимость от #29:** указана в «Глобальных ограничениях» (он перемещает `pipelines/_shared/steps.py` + `main.py`). ✔
- **Согласованность типов:** ключи `ENGINE_FLOWS` идентичны в T3; `DEFAULT_ENGINES=("dbt","bruin")` используется в T1/T4/T6. ✔
- **Риск:** наибольший радиус поражения; изоляция worktree+PR + последовательность T1/T2-до-перемещения его сдерживают. ADR-0020 фиксирует разворот hard rule «SQLMesh — это production».

## Передача выполнения

План сохранён. Два варианта выполнения: **(1) Subagent-Driven (рекомендуется)** — свежий субагент на задачу + двухстадийное ревью; **(2) Inline** — executing-plans с чекпоинтами. Выполнение стартует, как только **PR #29 смёржен** и worktree ответвлён от `dev` после #29.
