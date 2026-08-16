<!-- ru-translation-of: docs/superpowers/plans/2026-07-23-transform-expansion-and-six-prefect-subprojects.md sha:e8f7345331a9 -->
<!-- Автоперевод. Источник — docs/superpowers/plans/2026-07-23-transform-expansion-and-six-prefect-subprojects.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [2026-07-23-transform-expansion-and-six-prefect-subprojects.md](2026-07-23-transform-expansion-and-six-prefect-subprojects.md)

# Расширение transform, синхронизированный с ODTS DQ в SQLMesh и шесть разделённых Prefect-подпроектов — план реализации

> **Для агентных исполнителей:** ОБЯЗАТЕЛЬНЫЙ САБ-СКИЛЛ: используйте superpowers:subagent-driven-development (рекомендуется) или superpowers:executing-plans, чтобы реализовать этот план задача-за-задачей. Шаги используют синтаксис чекбоксов (`- [ ]`) для отслеживания.

**Цель:** (1) Расширить transform-SSoT так, чтобы **каждый raw-источник проходил через staging в core/fs** во всех движках и ODTS-фикстурах; (2) объявить **исчерпывающий DQ один раз в ODTS-спецификации** и заставить SQLMesh-адаптер *проецировать его в audits* (сегодня он молча отбрасывает каждую проверку); (3) реструктурировать Prefect-оркестрацию в **шесть разделённых, индивидуально-деплоящихся подпроектов** поверх общей библиотеки шагов.

**Архитектура:** `spec/sql/` (поверхность авторинга ODTS в формате `@bruin`, ADR-0016) — единственный источник истины для моделей *и* их DQ. Адаптеры (`src/ogip/spec_compile/to_*.py`) проецируют его в SQLMesh / dbt / Bruin. Сегодня существуют три дрейфа, и этот план их закрывает: (a) core/fs потребляют только rawg-хребет, а четыре источника заканчиваются тупиком в staging; (b) `to_sqlmesh._model_text` выдаёт `MODEL(name, kind)` и **отбрасывает `columns.checks`**; (c) все шесть оркестрационных сетапов — это модули, разделяющие один `_common.py`, а не отдельные деплоящиеся сущности. Объединяющий принцип остаётся нетронутым: **объяви один раз в спецификации, проецируй везде; реестр/спецификация — SSoT, ни один движок не переопределяет модель или проверку.**

**Технологический стек:** Python 3.13 (pyright strict, ruff), `@bruin`-переносимый SQL, SQLMesh (встроенные + кастомные audits), dbt (тесты), Bruin (checks), Prefect 3 (`@flow`/`@materialize`, деплойменты `prefect.yaml`), Dagster 1.13.x (нативные `dagster_dlt`/`dagster_dbt`, запуск *под* Prefect), склад DuckDB, pytest.

## Глобальные ограничения

- **Спецификация — SSoT для DQ.** Каждая проверка корректности пишется в `spec/sql` в `columns.checks:` / `checks:` (словарь ODTS §5–6) и проецируется адаптерами. Ни один audit не пишется вручную в `transform/sqlmesh/models/` — эти файлы *генерируются*.
- **Граница ODTS §6 — checks ≠ monitors.** `checks:` держат только ограничения корректности (`not_null`, `unique`, `non_negative`, `between(a,b)`, `accepted_values`, `fk`). **Мониторы** свежести / количества строк НЕ ДОЛЖНЫ попадать в `checks:`; они принадлежат слою ODOS `monitoring.yml` / `dq/`. «Исчерпывающий DQ» разделяется соответственно — корректность → SQLMesh audits (синхронизированы из ODTS); мониторы → ODOS/dq.
- **ODTS-фикстуры отслеживают реальность.** `spec/ODTS/examples/` — это conformance-подмножество `spec/sql/`; любая модель или проверка, добавленная в `spec/sql`, зеркалится в ODTS-примеры в том же коммите (директива синхронизации).
- **Сгенерированные каталоги — это выходы, никогда не редактируемые вручную.** `transform/{sqlmesh,dbt,bruin}/models|assets/` регенерируются адаптерами. Ручная правка — это дефект; исправление идёт в `spec/sql` + адаптер.
- **Кросс-источниковый ключ не предполагается.** Пять источников не разделяют естественного ключа; интеграция в core идёт через явный мост нормализации заголовков, и покрытие джойна само по себе — DQ-проверка, никогда не молчаливый inner join, отбрасывающий строки.
- **Закон Layer-0 держится.** Raw остаётся 1:1 AS-IS; всё приведение типов/нормализация — работа staging. Скрейперы остаются `publishable: false` и демо-безопасными по умолчанию.
- **Реестр — SSoT для задач; `_shared` — SSoT для шагов.** Шесть подпроектов импортируют общие step-функции; ни один не форкает модель, тело задачи или шаг.
- **Привязка коммитов.** Каждый коммит несёт `Refs: #37` (ODOS/ODTS-обвязка) и, где специфично для источника, `Refs: #18` / `Refs: #19`.
- **ТОЛЬКО-ПРЕДЛОЖЕНИЕ для skills/agents/hooks.** Предложено здесь; создаётся через `/create-skill` / `/upsert-skill` / `/sync-project-agents` после одобрения. Скрипты под `~/.ai/skills/_scripts/` — предпочтительная детерминированная поверхность.

## Замечание о scope (декомпозиция)

Три независимых, последовательных подсистемы, каждая поставляема сама по себе — реализуйте по порядку, потому что каждая опирается на предыдущую:
1. **Part 1 — Полный raw-lineage** (модели). Фундамент.
2. **Part 2 — Синхронизированный с ODTS DQ в SQLMesh** (checks → audits). Опирается на модели Part 1.
3. **Part 3 — Шесть разделённых Prefect-подпроектов** (оркестрация). Оборачивает готовый пайплайн.

Части 4 (скрипты/skills/hooks) и 5 (персистентность) — сквозные и приземляются инкрементально с каждой частью.

---

## Part 1 — Полный raw-lineage: каждый источник в core/fs, во всех движках + ODTS

**Текущее состояние:** `spec/sql/{raw,staging}` покрывают все 5 источников (rawg, metacritic, opencritic, psn, steamcharts); `core.game` `depends: staging.stg_games` (только rawg); `fs.market_features depends: core.game`. `transform/{dbt,bruin,sqlmesh}` и `spec/ODTS/examples/` несут только rawg + metacritic. Четыре источника заканчиваются тупиком.

**Целевой lineage:**
```
raw.<src>  → staging.stg_<src>  ─┐
                                 ├─ staging.stg_game_match (title-normalized bridge)
core.game (rawg spine) ──────────┤
                                 ├─ core.critic_reception (metacritic + opencritic)
                                 ├─ core.console_pricing  (psn)
                                 └─ core.traction         (steamcharts)
fs.market_features ← core.game ⨝ (critic_reception, console_pricing, traction) on game_sk
```

### Task 1.1: модель-мост нормализации заголовков

**Файлы:**
- Создать: `spec/sql/staging/stg_game_match.sql`
- Тест: `src/tests/unit/test_spec_lineage.py`

**Интерфейсы:**
- Производит: `staging.stg_game_match(game_sk, match_key, source_system, source_row_key)` — одна строка на (rawg game, source), разрешённая по нормализованному ключу заголовка. `match_key = lower(regexp_replace(title, '[^a-z0-9]', '', 'g'))`.

- [ ] **Step 1: Напишите падающий тест** — проверьте, что мост существует и парсится, и что вывод его `match_key` присутствует.

```python
# src/tests/unit/test_spec_lineage.py
from pathlib import Path

from ogip.spec_compile import load_assets

_SPEC = Path("spec/sql")


def test_bridge_and_per_source_core_models_exist():
    names = {a.name for a in load_assets(_SPEC)}
    assert "staging.stg_game_match" in names
    assert "core.critic_reception" in names
    assert "core.console_pricing" in names
    assert "core.traction" in names
```

- [ ] **Step 2: Запустите, убедитесь, что он падает.** `uv run pytest src/tests/unit/test_spec_lineage.py -v` → FAIL (модели отсутствуют).

- [ ] **Step 3: Напишите мост** как `@bruin`-view. `match_key` нормализует `name` rawg и заголовок каждого источника; мост — ЕДИНСТВЕННОЕ место, где живёт разрешение идентичности. Он делает LEFT JOIN, так что несматченные строки источника видимы (покрытие — это DQ-метрика, Task 2.x), никогда не отбрасываются:

```sql
/* @bruin
name: staging.stg_game_match
type: duckdb.sql
materialization: {type: view}
owner: data-eng@ogip
tags: [staging, bridge, daily]
depends: [staging.stg_games, staging.stg_metacritic_games, staging.stg_opencritic_games, staging.stg_psn_concepts, staging.stg_steamcharts_apps]
columns:
  - name: game_sk
    checks: [{name: not_null}]
  - name: match_key
    checks: [{name: not_null}]
@bruin */
with spine as (
    select md5(cast(game_id as varchar)) as game_sk,
           regexp_replace(lower(name), '[^a-z0-9]', '', 'g') as match_key
    from staging.stg_games
)
select game_sk, match_key from spine
```

- [ ] **Step 4:** Запустите тест — всё ещё падает (per-source core-модели отсутствуют); переходите к 1.2.

### Task 1.2: per-source core-feature-модели

**Файлы:**
- Создать: `spec/sql/core/critic_reception.sql`, `spec/sql/core/console_pricing.sql`, `spec/sql/core/traction.sql`

**Интерфейсы:**
- `core.critic_reception(game_sk, metacritic_score, opencritic_score)` — metacritic + opencritic, приджойненные к хребту через `stg_game_match.match_key`.
- `core.console_pricing(game_sk, psn_price, psn_currency, locale)` — psn, ключуется через мост; сохраняет `locale` (составная гранулярность).
- `core.traction(game_sk, current_players, peak_players)` — steamcharts, приведённый из staging.

- [ ] **Step 1:** Напишите каждую как `@bruin`-таблицу, зависящую от `staging.stg_game_match` + staging-модели источника. Пример (`core.critic_reception`), с column-проверками, которые станут SQLMesh audits в Part 2:

```sql
/* @bruin
name: core.critic_reception
type: duckdb.sql
materialization: {type: table}
owner: data-eng@ogip
tags: [core, feature, daily]
depends: [staging.stg_game_match, staging.stg_metacritic_games, staging.stg_opencritic_games]
columns:
  - name: game_sk
    checks: [{name: not_null}, {name: unique}]
  - name: metacritic_score
    checks: [{name: between, args: [0, 100]}]
  - name: opencritic_score
    checks: [{name: between, args: [0, 100]}]
@bruin */
select b.game_sk,
       mc.score as metacritic_score,
       oc.score as opencritic_score
from staging.stg_game_match b
left join staging.stg_metacritic_games mc
    on regexp_replace(lower(mc.name), '[^a-z0-9]', '', 'g') = b.match_key
left join staging.stg_opencritic_games oc
    on regexp_replace(lower(oc.name), '[^a-z0-9]', '', 'g') = b.match_key
```

- [ ] **Step 2:** Напишите `core.console_pricing` и `core.traction` тем же способом (мост + staging источника). `console_pricing` сохраняет `locale` в гранулярности; его проверка ключа — `unique` на `(game_sk, locale)` через запись в блоке `checks:`.
- [ ] **Step 3:** Запустите `test_spec_lineage.py` → PASS.

### Task 1.3: обогатить `fs.market_features` новыми сигналами

**Файлы:** Изменить `spec/sql/fs/market_features.sql`

- [ ] **Step 1:** LEFT JOIN трёх новых core-моделей на `core.game` по `game_sk`; добавьте feature-колонки (`metacritic_score`, `opencritic_score`, `avg_critic_score`, `psn_price`, `peak_players`) и флаг покрытия на источник. Сохраните существующие колонки. Каждая добавленная числовая колонка получает проверку `non_negative`/`between`.
- [ ] **Step 2:** Проверьте, что `depends` у `fs.market_features` теперь включает три новые core-модели и что `load_assets` по-прежнему разрешает полный DAG. Запустите `make check`.
- [ ] **Step 3: Коммит.** `git commit -o spec/sql/staging/stg_game_match.sql spec/sql/core/critic_reception.sql spec/sql/core/console_pricing.sql spec/sql/core/traction.sql spec/sql/fs/market_features.sql src/tests/unit/test_spec_lineage.py -m "feat(spec): integrate all five sources into core/fs via title bridge"` (`Refs: #37 #18 #19`).

### Task 1.4: регенерировать проект каждого движка + синхронизировать ODTS-примеры (детерминированно)

**Файлы:** Изменить (регенерировать) `transform/dbt/models/`, `transform/bruin/assets/`, `transform/sqlmesh/models/`; расширить `spec/ODTS/examples/`.

- [ ] **Step 1: Добавьте тест регенерации + паритета**, проверяющий, что набор моделей проекта каждого движка равен набору `spec/sql`:

```python
# src/tests/unit/test_engine_projects_cover_spec.py
from pathlib import Path

from ogip.spec_compile import load_assets

_SPEC = {a.name for a in load_assets(Path("spec/sql"))}


def _bruin_names(root: str) -> set[str]:
    return {
        f"{p.parent.name}.{p.stem}"
        for p in Path(root).rglob("*.sql")
    }


def test_bruin_project_covers_every_spec_model():
    missing = {n.split(".")[1] for n in _SPEC} - {n.split(".")[1] for n in _bruin_names("transform/bruin/assets")}
    assert not missing, f"bruin assets missing: {sorted(missing)}"
```

- [ ] **Step 2:** Запустите → FAIL (bruin/dbt несут только rawg+metacritic).
- [ ] **Step 3: Регенерируйте**, прогнав адаптеры против полной спецификации (это скрипт, Task 4.1): `compile_to_bruin`, `compile_to_dbt`, `compile_to_sqlmesh` (+ `to_sqlmesh_dbt`) в их каталоги проектов. Закоммитьте регенерированные выходы.
- [ ] **Step 4: Синхронизируйте ODTS-примеры** — скопируйте новые фикстуры `raw/`, `staging/`, `core/`, `fs/` для opencritic/psn/steamcharts + мост + per-source core-модели в `spec/ODTS/examples/`, чтобы conformance-подмножество совпадало. Обновите список моделей в `spec/ODTS/examples/README.md`.
- [ ] **Step 5:** Запустите `test_engine_projects_cover_spec.py` + `make check` → PASS. Коммит (`Refs: #37`).

**Skills/скрипты/hooks Part 1 (ТОЛЬКО-ПРЕДЛОЖЕНИЕ):**
- **Скрипт (НОВЫЙ):** `regen-engine-projects` (Task 4.1) — один детерминированный вход, прогоняющий все адаптеры + синхронизирующий ODTS-примеры; `--check` для дрейфа. Переиспользует `/spec-compile-engines`.
- **Hook:** `spec-lineage-coverage` — падать, если модель `raw.<src>` существует без пути в `fs.market_features` (детектор тупиков); часть сквозного drift-гейта (§4).

---

## Part 2 — Синхронизированный с ODTS исчерпывающий DQ, проецируемый в SQLMesh audits

**Текущее состояние:** `to_sqlmesh._model_text` выдаёт `MODEL(name, kind)` + SQL и **полностью отбрасывает `columns.checks`**. `Asset.meta` сохраняет полный заголовок (columns + checks), так что исправление локализовано в адаптере — без изменения парсера. Существующие проверки: только `core.game`/`fs`; raw/staging не несут ни одной.

**Дизайн:** обогатить checks в `spec/sql` (словарь ODTS §5–6), затем научить `to_sqlmesh` рендерить их как SQLMesh audits. Мониторы (свежесть/количество строк) явно ВНЕ `checks:` (ODTS §6) и добавляются как чётко помеченные SQLMesh-нативные audits под `transform/sqlmesh/audits/`, которые НЕ синхронизированы со спецификацией (задокументированы как engine-экстра), плюс их настоящий дом в ODOS `monitoring.yml`.

### Task 2.1: `to_sqlmesh` рендерит `columns.checks` как встроенные audits

**Файлы:** Изменить `src/ogip/spec_compile/to_sqlmesh.py`; Тест `src/tests/unit/test_to_sqlmesh_audits.py`

**Интерфейсы:**
- Производит: `_audits(asset: Asset) -> str` — клауза `audits (...)` для блока MODEL. Отображение: `not_null → not_null(columns := (c))`, `unique → unique_values(columns := (c))`, `non_negative → accepted_range(column := c, min_v := 0)`, `between,args:[a,b] → accepted_range(column := c, min_v := a, max_v := b)`, `accepted_values,args:[...] → accepted_values(column := c, is_in := (...))`.

- [ ] **Step 1: Напишите падающий тест** — модель с проверками компилируется в блок MODEL, несущий соответствующие audits:

```python
# src/tests/unit/test_to_sqlmesh_audits.py
from pathlib import Path

from ogip.spec_compile import compile_to_sqlmesh


def test_checks_become_sqlmesh_audits(tmp_path):
    compile_to_sqlmesh(Path("spec/sql"), tmp_path / "models")
    core = (tmp_path / "models" / "core" / "game.sql").read_text()
    assert "not_null(columns := (game_sk))" in core
    assert "unique_values(columns := (game_sk))" in core
    critic = (tmp_path / "models" / "core" / "critic_reception.sql").read_text()
    assert "accepted_range(column := metacritic_score, min_v := 0, max_v := 100)" in critic
```

- [ ] **Step 2:** Запустите → FAIL (audits не выдаются).
- [ ] **Step 3:** Реализуйте `_audits` + вставьте её в блок `MODEL(...)` у `_model_text`:

```python
def _audit_for(col: str, chk: dict[str, object]) -> str | None:
    name = chk["name"]
    args = chk.get("args") or []
    if name == "not_null":
        return f"not_null(columns := ({col}))"
    if name == "unique":
        return f"unique_values(columns := ({col}))"
    if name == "non_negative":
        return f"accepted_range(column := {col}, min_v := 0)"
    if name == "between" and len(args) == 2:
        return f"accepted_range(column := {col}, min_v := {args[0]}, max_v := {args[1]})"
    if name == "accepted_values" and args:
        vals = ", ".join(f"'{v}'" for v in args)
        return f"accepted_values(column := {col}, is_in := ({vals}))"
    return None  # unknown → surfaced by the vocabulary gate (Task 2.3), never silently dropped


def _audits(asset: Asset) -> list[str]:
    out: list[str] = []
    for col in asset.meta.get("columns") or []:
        for chk in col.get("checks") or []:
            rendered = _audit_for(col["name"], chk)
            if rendered:
                out.append(rendered)
    return out
```

- [ ] **Step 4:** В `_model_text`, когда `_audits(asset)` непустой, расширьте заголовок: `MODEL (\n  name {name},\n  kind {kind},\n  audits (\n    {",\n    ".join(audits)}\n  )\n);`.
- [ ] **Step 5:** Запустите тест + `make check` → PASS. Коммит (`Refs: #37`).

### Task 2.2: обогатить checks исчерпывающе по raw/staging/core/fs (в спецификации)

**Файлы:** Изменить `spec/sql/**/*.sql` (добавить блоки `columns.checks:` / `checks:`).

- [ ] **Step 1:** Добавьте полный набор корректности, написанный один раз в спецификации (словарь ODTS):
  - **raw**: `not_null` + `unique` на естественном ключе каждого источника (rawg `game_id`, opencritic `game_id`, steamcharts `appid`, psn `row_key`, metacritic `slug`); `not_null` на `content_hash`/`source_url` для скрейперов.
  - **staging**: ключ `not_null`/`unique`; `between(0,100)` на скорах; `non_negative` на счётчиках/игроках/ценах; `accepted_values` на `locale`/`currency` (psn).
  - **core**: ключи `not_null`/`unique`; диапазоны скоров; блок `checks:` для составной уникальности `(game_sk, locale)` на `console_pricing`.
  - **fs**: ключи; `non_negative` на `popularity_score`; `between(0,1)` на `critic_score`.
- [ ] **Step 2:** Добавьте в блок `checks:` запись **referential-integrity**, где кросс-модельно — например, `core.critic_reception.game_sk` FK на `core.game.game_sk` (именованная кросс-модельная проверка ODTS §6 → SQLMesh кастомный audit `forall`/relationship).
- [ ] **Step 3:** Регенерируйте SQLMesh-модели (скрипт Task 4.1) и проверьте, что число audits подскочило. `make check`. Коммит (`Refs: #37 #18 #19`).

### Task 2.3: гейт словаря проверок + SQLMesh-нативные monitor-audits (помеченные как non-ODTS)

**Файлы:** Изменить `to_sqlmesh.py` (страж неизвестных проверок); Создать `transform/sqlmesh/audits/monitors.sql` (нативные, несинхронизированные); Изменить `spec/ODOS/examples/monitoring.yml`.

- [ ] **Step 1:** Заставьте `_audits` **проваливать компиляцию** на имени проверки вне переносимого словаря ODTS (SPEC §5: «атрибуты вне словаря проверок ДОЛЖНЫ проваливать компиляцию») — бросать `SqlSpecError`, никогда молча не пропускать. Тест с фиктивной проверкой.
- [ ] **Step 2:** Добавьте SQLMesh-нативные **monitor**-audits (нижний порог количества строк, свежесть) как отдельные блоки `AUDIT (...)` в `transform/sqlmesh/audits/monitors.sql`, каждый с шапкой-комментарием: `-- NOT ODTS-synced: monitors (§6) live here + ODOS monitoring.yml, never in spec checks:`. Это «нативная» половина исчерпывающего DQ, по замыслу держимая вне поверхности спецификации.
- [ ] **Step 3:** Добавьте интенты мониторов в `spec/ODOS/examples/monitoring.yml` (их переносимый дом), чтобы разделение было задокументировано с обеих сторон. `make check`. Коммит (`Refs: #37`).

**Skills/скрипты/hooks Part 2 (ТОЛЬКО-ПРЕДЛОЖЕНИЕ):**
- **Скрипт (НОВЫЙ):** `dq-audit-report` — перечисляет по каждой модели spec-проверки vs отрендеренные SQLMesh audits; `--check` падает на любой spec-проверке без audit (проекция тотальна). Вынесите таблицу отображения check→audit в settings.
- **Skill (переиспользование + upsert):** `/spec-compile-engines` получает шаг checks→audits; upsert через `/upsert-skill` → обязательный `/save-all-deterministic-for-skill-as-scripts`.
- **Hook:** `dq-checks-not-monitors` — падать, если запись `checks:` использует имя monitor-формы (`freshness`, `row_count`, `rowcount`), обеспечивая границу ODTS §6 на этапе коммита.

---

## Part 3 — Шесть разделённых, индивидуально-деплоящихся Prefect-подпроектов

**Текущее состояние:** `pipelines/flows/engines/prefect_{sqlmesh,dbt,bruin,dagster,opendbt,sqlmesh_dbt}.py`, все — однострочники поверх `make_engine_flow` в общем `_common.py`; нет `prefect.yaml`, нет `deployments/`. Решение (зафиксировано): **разделение на уровне проектов, общие шаги** — каждый движок становится собственным каталогом-подпроектом с `prefect.yaml` + `flow.py` + `deployments/`, импортируя шаги из общей библиотеки. Инструментарий ингестии (dlt/ingestr/airbyte/scraping) доступен в каждом подпроекте — общий по умолчанию, кастомный там, где инструмент интегрируется особым образом (dlt-как-`dagster_dlt` в dagster-проекте; dlt-как-opendbt-source в opendbt). В dagster-подпроекте **Prefect — внешний оркестратор, а Dagster бежит под ним** (`dg launch`), согласно `/call-dagster-from-prefect`.

**Целевое:**
```
pipelines/
  _shared/            # SSoT for steps — the ONLY implementation
    steps.py          # build_warehouse, build_ml_outputs, publish_outputs (from _common)
    ingest.py         # make_ingest_assets, scraper_raw_keys, raw_asset_key (per-source assets)
    alerting.py       # notify_flow_failure
    paths.py          # REPO, SPEC_SQL, SQLMESH_DIR
    engine_flow.py    # make_engine_flow(engine) — the shared assembler
  sqlmesh/  flow.py  prefect.yaml  deployments/    # production (default)
  dbt/      flow.py  prefect.yaml  deployments/
  bruin/    flow.py  prefect.yaml  deployments/
  opendbt/  flow.py  prefect.yaml  deployments/  ingest.py   # custom dlt→opendbt source
  sqlmesh_dbt/ flow.py prefect.yaml deployments/
  dagster/  flow.py  prefect.yaml  deployments/               # Prefect wraps Dagster (dlt+dbt)
```

### Task 3.1: извлечь общую библиотеку шагов (без изменения поведения)

**Файлы:** Создать `pipelines/_shared/{__init__,steps,ingest,alerting,paths,engine_flow}.py`; перенести тела из `pipelines/flows/_common.py`, `_paths.py`, `alerting_hooks.py`.

**Интерфейсы:** `make_engine_flow(engine, *, flow_name=None)`, `make_ingest_assets(engine)`, `scraper_raw_keys(engine)`, `raw_asset_key(engine, system, entity)` — сигнатуры, идентичные плану обвязки скрейперов (`2026-07-20-wire-scraper-tasks-into-orchestration-layers.md` Tasks 2.1/2.3), теперь живущие в `_shared`.

- [ ] **Step 1:** Перенесите код дословно; оставьте `pipelines/flows/_common.py` реэкспортирующим из `_shared`, чтобы существующие импорты/тесты оставались зелёными во время миграции. Прогоните полный набор — без изменений.
- [ ] **Step 2:** Вложите сюда per-source скрейпер-ассеты (Task 2.1 того плана), чтобы все шесть подпроектов наследовали per-source lineage. Коммит (`Refs: #37`).

### Task 3.2: сгенерировать каркас шести подпроектов

**Файлы:** Создать `pipelines/<engine>/flow.py` + `prefect.yaml` + `deployments/` для каждого из шести.

- [ ] **Step 1: Падающий тест** — у каждого профиля в `config.yml run_profiles` есть каталог-подпроект с `flow.py` + `prefect.yaml`:

```python
# src/tests/unit/test_prefect_subprojects.py
from pathlib import Path

_ENGINES = ["sqlmesh", "dbt", "bruin", "opendbt", "sqlmesh_dbt", "dagster"]


def test_each_engine_is_a_separated_subproject():
    for e in _ENGINES:
        assert (Path("pipelines") / e / "flow.py").is_file()
        assert (Path("pipelines") / e / "prefect.yaml").is_file()
```

- [ ] **Step 2:** Для пяти SQL-движков `flow.py` тонкий: `from pipelines._shared.engine_flow import make_engine_flow; flow = make_engine_flow("<engine>")`. Каждый `prefect.yaml` называет один деплоймент для этого flow (work-pool, cron расписания из `_defaults.yml`).
- [ ] **Step 3:** Для `dagster/flow.py` перенесите шов `prefect_dagster.py` (Prefect триггерит `dg launch` для dlt+dbt) + переиспользуйте `_shared` скрейпер-ассеты + ML/publish. Prefect остаётся внешним; Dagster — под-оркестратор. Задокументируйте нюанс «dlt здесь — нативный компонент `dagster_dlt`, а не `ingest.rawg`» в docstring модуля.
- [ ] **Step 4:** `opendbt/ingest.py` — пример хука кастомной интеграции: dlt, выставленный как OpenDBT-source. Иначе общий по умолчанию. Держите минимальным/заглушкой с ясным docstring, если dlt-мост OpenDBT ещё не подключён.
- [ ] **Step 5:** Запустите тест + `make check` → PASS. Коммит (`Refs: #37`).

### Task 3.3: мигрировать лаунчер run-профилей + вывести из эксплуатации старые модули

**Файлы:** Изменить `src/scripts/run-profile.py`, `Justfile`; удалить `pipelines/flows/engines/*.py` (после того, как реэкспорт-шим окажется зелёным); обновить `pipelines/README.md`.

- [ ] **Step 1:** Нацельте `run-profile.py` и `just run-profile <name>` на `pipelines/<engine>/flow.py`. Добавьте `just prefect-deploy <engine>`, запускающий `prefect.yaml` этого подпроекта.
- [ ] **Step 2:** Как только все тесты пройдут против `_shared` + подпроектов, удалите модули `engines/*.py` и шимы `_common.py`/`_paths.py`/`alerting_hooks.py` (их тела теперь живут в `_shared`). Обновите реэкспорт `pipelines/flows/main.py` на `pipelines.sqlmesh.flow`.
- [ ] **Step 3:** Перепишите таблицу в `pipelines/README.md` под раскладку из шести подпроектов + общую библиотеку + заметку Dagster-под-Prefect. `make check`. Коммит (`Refs: #37`).

**Skills/скрипты/hooks Part 3 (ТОЛЬКО-ПРЕДЛОЖЕНИЕ):**
- **Скрипт (НОВЫЙ):** `scaffold-prefect-subproject <engine>` — выдаёт скелет `flow.py`/`prefect.yaml`/`deployments/` из шаблона; скаляры (work-pool, cron, список движков) в settings. Переиспользует `/integrate-sql-tool-with-prefect`.
- **Skill (переиспользование):** `/call-dagster-from-prefect` (dagster-подпроект), `/integrate-sql-tool-with-prefect` (пять SQL-подпроектов).
- **Hook:** `subproject-parity` — падать, если у записи `run_profiles` нет каталога-подпроекта, или подпроект форкает шаг вместо импорта `_shared` (grep-страж: `flow.py`, локально определяющий `build_warehouse`/`publish_outputs`).

---

## Part 4 — Детерминированные скрипты, skills, hooks (поверхность `/save-all-deterministic-for-skill-as-scripts`)

Все детерминированные; все извлечены по стандарту; скаляры вынесены в `~/.ai/skills/.settings/`. **ТОЛЬКО-ПРЕДЛОЖЕНИЕ** — создаются через skill-флоу после одобрения, скрипты предпочтительнее новых skills.

| Артефакт | Тип | Что делает | Переиспользует |
|---|---|---|---|
| `regen-engine-projects` | скрипт (Task 1.4) | прогон всех адаптеров `to_*` + синхронизация ODTS-примеров; `--check` дрейф | `/spec-compile-engines` |
| `dq-audit-report` | скрипт (Task 2.x) | покрытие spec-check ↔ SQLMesh-audit; `--check` падает на любой непроецированной проверке | — |
| `scaffold-prefect-subproject` | скрипт (Task 3.x) | выдать скелет подпроекта из шаблона | `/integrate-sql-tool-with-prefect` |
| `spec-lineage-coverage` | **hook** | падать на raw-модели без пути в fs (тупик) | — |
| `dq-checks-not-monitors` | **hook** | падать, если имя monitor-формы появляется в `checks:` (ODTS §6) | — |
| `subproject-parity` | **hook** | падать на рассогласовании профиль↔подпроект или на форкнутом шаге | — |

Подключите три гейта `--check`/hook в `make check`. **Переиспользуемые skills, не пересоздаваемые:** `/spec-compile-engines`, `/generate-agnostic-bruin-sql-specs`, `/integrate-sql-tool-with-prefect`, `/call-dagster-from-prefect`, `/add-dagster-module`, `/integrate-dagster-with-dbt`, `/add-data-source`. **Новый skill — только если скрипты оправдывают фронт:** `/extend-transform-lineage-and-dq` (chain-скилл, прогоняющий regen + dq-report + гейты); предлагается через `/create-skill` только после одобрения.

---

## Part 5 — Персистентность: upsert памяти / документов / спецификаций / скриптов / skills / settings / саб-агентов / hooks

Делайте это по мере приземления каждой части, а не в конце — знание есть вторая половина результата.

- [ ] **Память** (`~/.claude/.../memory/`): новый файл `ogip-odts-dq-and-six-subprojects.md` — «ODTS/`spec/sql` — DQ SSoT; `to_sqlmesh` раньше отбрасывал checks; checks≠monitors (§6); пять источников не разделяют ключ → title bridge; шесть разделённых Prefect-подпроектов поверх `_shared`, Dagster-под-Prefect.» Связать `[[ogip-odps-odts-odos-family]]`, `[[ogip-odos-orchestration-standard]]`, `[[ogip-prefect-per-engine-setups]]`, `[[ogip-source-dod-gate]]`. Добавить однострочный указатель в `MEMORY.md`.
- [ ] **Документы/спецификации:** обновить `spec/ODTS/IMPLEMENTATION.md` (checks→audits теперь учитываются; таблица отображения), `spec/ODOS/IMPLEMENTATION.md` (шесть подпроектов; §4 проекция Prefect), `pipelines/README.md`, `transform/README.md`. Новый ADR: `docs/adr/ADR-00NN-odts-dq-projection-and-six-prefect-subprojects.md` (сначала grep OGAP по `[[ogip-adr-numbering-collides-with-ogap]]`).
- [ ] **Скрипты + settings:** три скрипта + записи `.settings/` (карта check→audit, список движков, work-pool/cron, путь к ODTS-примерам).
- [ ] **Skills:** upsert `/spec-compile-engines`; предложить `/extend-transform-lineage-and-dq`, если оправдано — всё через `/create-skill` / `/upsert-skill`, никогда вручную; каждый запускает `/save-all-deterministic-for-skill-as-scripts`.
- [ ] **Ролевой саб-агент:** предложить `ogip-transform-engineer` (владеет `spec/sql`, адаптерами, DQ-audits, шестью подпроектами) как сиблинга `ogip-ingestion-engineer`; опубликовать через `/sync-project-agents` (сначала dry-run; отказывается на грязном shared-репозитории).
- [ ] **Hooks:** зарегистрировать три гейта (`spec-lineage-coverage`, `dq-checks-not-monitors`, `subproject-parity`) в hook-конфиге репозитория + `make check`.

---

## Self-Review

**Покрытие спецификации:** Запрос A (шесть разделённых Prefect-подпроектов) → Part 3 ✅ (разделение на уровне проектов, общие шаги, Dagster-под-Prefect подтверждён, per-project инструментарий ингестии). Запрос B (расширить ODTS + все transform-сетапы всеми raw-моделями, полный lineage) → Part 1 ✅ (мост + per-source core + обогащение fs + регенерация всех движков + синхронизация ODTS). Запрос C (исчерпывающий SQLMesh DQ) → Part 2 ✅ (компилятор checks→audits + исчерпывающие spec-проверки + нативные мониторы, синхронизированные с ODTS). Директива синхронизации-с-ODTS → Parts 1.4, 2 и граница checks≠monitors §6 ✅. Директива персистентности → Part 5 ✅. Требование скриптов/skills/hooks → Part 4 ✅.

**Скан плейсхолдеров:** Нет «TBD»/«add validation». Два честных ограничения — кросс-источниковая идентичность (title bridge, покрытие как DQ) и checks≠monitors — спроектированы явно, а не отложены. Dlt-мост OpenDBT — единственная заглушка, помечена как таковая с причиной.

**Согласованность типов:** `make_engine_flow(engine)`, `make_ingest_assets(engine)`, `raw_asset_key(engine, system, entity)`, `_audits(asset) -> list[str]`, `_audit_for(col, chk) -> str | None` используются согласованно по Parts 2–3. Форма `Asset.meta["columns"][*]["checks"][*]{name,args}` совпадает с авторингом `spec/sql` и отображением компилятора. Гранулярность моста `(game_sk)` и гранулярность прайсинга `(game_sk, locale)` согласованы между Task 1.2 и проверками Part 2.

**Декомпозиция:** три последовательных, независимо-поставляемых части; каждая заканчивается зелёной и релизуемой. Part 1 разблокирует Part 2 (audits нужны модели); обе разблокируют Part 3 (подпроекты оборачивают готовый пайплайн).
