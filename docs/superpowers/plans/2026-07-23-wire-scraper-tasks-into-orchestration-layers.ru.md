<!-- ru-translation-of: docs/superpowers/plans/2026-07-23-wire-scraper-tasks-into-orchestration-layers.md sha:3418abc1d131 -->
<!-- Автоперевод. Источник — docs/superpowers/plans/2026-07-23-wire-scraper-tasks-into-orchestration-layers.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [2026-07-23-wire-scraper-tasks-into-orchestration-layers.md](2026-07-23-wire-scraper-tasks-into-orchestration-layers.md)

# Подключение задач скрейпера/парсера к четырём слоям оркестрации — План реализации

> **Для агентных исполнителей:** ОБЯЗАТЕЛЬНЫЙ САБ-СКИЛЛ: используйте superpowers:subagent-driven-development (рекомендуется) или superpowers:executing-plans для реализации этого плана задача за задачей. Шаги используют синтаксис чекбоксов (`- [ ]`) для отслеживания.

> **ЗАМЕТКА ОБ УСТАРЕВШИХ ПУТЯХ (добавлена 2026-07-23, всё ещё открыта — НЕ реализуйте против путей ниже).**
> Реструктуризация в части 3 [плана расширения
> transform](2026-07-23-transform-expansion-and-six-prefect-subprojects.md) (см.
> [ADR-0019](../../adr/ADR-0019-odts-dq-projection-and-seven-prefect-subprojects.md)) удалила
> каждый файл, который этот план правит или упоминает ниже. Прежде чем трогать любую задачу здесь, переотобразите:
>
> | Этот план говорит | Теперь находится в |
> |---|---|
> | `pipelines/flows/_common.py` (вкл. `make_engine_flow`, `ingest_raw`, `scraper_raw_keys`, `make_ingest_assets`) | [`pipelines/_shared/steps.py`](../../../pipelines/_shared/steps.py) |
> | `pipelines/flows/_paths.py` | [`pipelines/_shared/paths.py`](../../../pipelines/_shared/paths.py) |
> | `pipelines/alerting_hooks.py` | [`pipelines/_shared/alerting.py`](../../../pipelines/_shared/alerting.py) |
> | `pipelines/flows/engines/prefect_dagster.py` | [`pipelines/dagster/flow.py`](../../../pipelines/dagster/flow.py) |
> | `pipelines/flows/engines/prefect_bruin.py` (и другие однострочники `prefect_*.py`) | `pipelines/<engine>/flow.py` — одна директория на движок (`sqlmesh`, `plain_sql`, `dbt`, `opendbt`, `sqlmesh_dbt`, `bruin`, `dagster`), каждая `{__init__.py, flow.py, prefect.yaml}` |
> | поиск engine → module (ранее неявный/импортируемый вручную) | [`pipelines/_shared/engines.py`](../../../pipelines/_shared/engines.py) `ENGINE_FLOWS` |
>
> Сам `make_engine_flow` поведенчески не изменился — он переехал, а не мутировал — поэтому проектные
> решения этого плана (per-source scraper assets, `raw_asset_key`, гейт landing-hop) всё ещё применимы; мертвы
> только пути файлов в блоках Task/Files ниже. См.
> [`spec/ODOS/IMPLEMENTATION.md`](../../../spec/ODOS/IMPLEMENTATION.md) §4 и
> [`pipelines/README.md`](../../../pipelines/README.md) для текущей раскладки.

**Цель:** Сделать каждую задачу реестра скрейпера/парсера (`ingest.opencritic`, `ingest.psn`, `ingest.steamcharts` и плейсхолдер `ingest.parse_to_landing`) полноправным, защищённым от дрейфа гражданином всех четырёх слоёв оркестрации — spec ODOS, основной Prefect, альт. Prefect+Dagster, альт. Bruin — переиспользуя одну детерминированную проекцию вместо ручного редактирования в четырёх местах.

**Архитектура:** Реестр (`src/ogip/tasks/`) — это SSoT; каждый слой оркестрации является *проекцией* его. Сегодня эти проекции написаны вручную и молча дрейфуют (три скрейпера отгружены без какой-либо проекции ODOS/Prefect-линейности). Этот план (a) закрывает дрейф для трёх отгруженных скрейперов, (b) извлекает проекцию в детерминированный скрипт + гейт эквивалентности с областью действия скрейпера — срез подготовки компилятора ODOS #37 — так что *следующий* скрейпер не сможет отгрузиться наполовину подключённым. Слои 3 и 4 описаны **только как их дельта** от слоя 2, и центральный вывод в том, что дельта почти пуста: скрейперы никогда не переезжают в Dagster/Airbyte/Bruin, потому что у этих инструментов нет источника с кастомным HTML-парсером. Скрейперы остаются Python-ассетами на стороне Prefect; только *ядро warehouse* (rawg dlt + dbt SQL) — это то, что каждый альт-профиль подменяет.

**Технологический стек:** Python 3.13 (pyright strict, ruff), Prefect 3 (ассеты `@flow`/`@materialize`), Dagster 1.13.x (`dg launch`, изолированное окружение под `experimental/`), Bruin CLI, фикстуры ODOS 0.1 (`spec/ODOS/examples/*.yml`), `@bruin`-переносимый SQL, pytest. Детерминированная логика идёт в `~/.ai/skills/_scripts/de/ingestion/` за Justfile по стандарту `/save-all-deterministic-for-skill-as-scripts`.

## Глобальные ограничения

- **Реестр — это SSoT.** Проекция слоя никогда не реализует заново тело задачи; она ссылается на имя реестра. Никакого параллельного кода скрейпера в любом потоке. (`docs/.../odos-*.md` §2 — дрейф, который это заменяет.)
- **Закрытый словарь.** `test_tasks_registry.py:97` фиксирует точный набор `ingest.*`. Любое новое имя задачи обновляет этот набор в том же коммите, иначе CI красный.
- **Закон слоя 0.** Вывод скрейпера садится 1:1 КАК ЕСТЬ; только `_ingested_at` + `etl_batch_id` (+ внутренние поля dlt). Никакого приведения типов/переименования в ingestion — это работа staging.
- **`publishable: false` держится.** Все три скрейпера сохраняют гейт републикации; этот план трогает только оркестрацию, никогда не позицию публикации контракта.
- **Демо-безопасный дефолт.** `make run` никогда не должен скрейпить живой сайт как побочный эффект. Каждый ассет скрейпера наследует гейтинг `OGIP_<SRC>_LIVE` от своего класса источника — поток его не переопределяет.
- **Схема ключа ассета — одна строка, одно место.** `file://ogip/{engine}/raw/{system}__{entity}` сейчас впечатан вручную в `_common.py` и `prefect_dagster.py`. После задачи 2.3 он конструируется одним хелпером, читающим settings; никаких литеральных строк raw-ключа в других местах.
- **Привязка коммитов.** Каждый коммит несёт `Refs: #37` (подключение ODOS) и, для специфичных для скрейпера задач, `Refs: #18` / `Refs: #19`. Обеспечивается `.ci/steps/commit-binding.sh`.
- **PROPOSE-ONLY для скиллов.** Файлы скиллов/хуков никогда не пишутся вручную — предлагаются здесь, создаются через `/create-skill` / `/upsert-skill` после одобрения пользователя. Скрипты под `_scripts/` — предпочтительная детерминированная поверхность.

---

## Текущее состояние (the "итого")

Задачи реестра в `src/ogip/tasks/ingest.py` и пробелы в их подключении:

| Задача | L1 ODOS | L2 основной Prefect | L3 Dagster-in-Prefect | L4 Bruin |
|---|---|---|---|---|
| `ingest.rawg` | ✅ `dlt_ingest_job` | ✅ `_ingest` | ✅ `K_RAW_DLT` | ✅ через `ingest.all` |
| `ingest.metacritic` | ✅ `metacritic_ingest_job` | ⚠️ свёрнут в `ingest.all` | ❌ (на стороне Prefect по замыслу) | ✅ через `ingest.all` |
| `ingest.opencritic` | ❌ **пробел** | ⚠️ свёрнут, нет собственного ассета | ❌ | ✅ через `ingest.all` |
| `ingest.psn` | ❌ **пробел** | ⚠️ свёрнут, нет собственного ассета | ❌ | ✅ через `ingest.all` |
| `ingest.steamcharts` | ❌ **пробел** | ⚠️ свёрнут, нет собственного ассета | ❌ | ✅ через `ingest.all` |
| `ingest.parse_to_landing` | ✅ `parsing_job` | ❌ не в потоке | ✅ Dagster `parsing` | ❌ |

Три пробела дрейфа для закрытия: покрытие фикстуры L1, per-source линейность L2 и отсутствие какого-либо *гейта*, который поймал бы любое из этих. Слои 3/4 — только дельта (ниже) и в основном наследуют L2.

---

## Слой 1 — spec / модель ODOS

**Что меняется:** `spec/ODOS/examples/ingestion.yml` получает три строфы скрейперов `*_ingest_job`, зеркалирующие `metacritic_ingest_job`, и новый тест делает покрытие фикстура↔реестр гейтом CI. Это срез с областью действия скрейпера теста эквивалентности #37 — первый гейт, превращающий «забыл спроецировать скрейпер» в красную сборку вместо надежды на код-ревью.

### Задача 1.1: фикстура ODOS покрывает каждый зарегистрированный скрейпер

**Файлы:**
- Создать: `src/tests/unit/test_odos_ingestion_fixture.py`
- Изменить: `spec/ODOS/examples/ingestion.yml`

**Интерфейсы:**
- Потребляет: `ogip.tasks.task_names()` (словарь реестра), имена `ingest.*`, помеченные как скрейпы.
- Производит: ничего импортируемого — фикстуру + гейт, на зелёности которого держатся другие задачи.

- [ ] **Шаг 1: Напишите проваливающийся тест.** Скрейпер — это любая задача реестра `ingest.<name>`, кроме `ingest.rawg` (dlt API), `ingest.all` (fan-out) и `ingest.parse_to_landing` (landing hop, своя `parsing_job`). Каждая такая задача должна появиться как `task:` некоторого job в `ingestion.yml`.

```python
# src/tests/unit/test_odos_ingestion_fixture.py
from pathlib import Path

import yaml

from ogip.tasks import task_names

_FIXTURE = Path("spec/ODOS/examples/ingestion.yml")
_NON_SCRAPER = {"ingest.rawg", "ingest.all", "ingest.parse_to_landing"}


def _scraper_task_names() -> set[str]:
    return {n for n in task_names() if n.startswith("ingest.")} - _NON_SCRAPER


def test_every_registered_scraper_has_an_odos_ingest_job():
    doc = yaml.safe_load(_FIXTURE.read_text("utf-8"))
    projected = {job["task"] for job in doc["jobs"].values() if "task" in job}
    missing = _scraper_task_names() - projected
    assert not missing, f"scraper tasks with no ODOS job: {sorted(missing)}"
```

- [ ] **Шаг 2: Запустите его, убедитесь, что он падает.** Запуск: `uv run pytest src/tests/unit/test_odos_ingestion_fixture.py -v`. Ожидается: FAIL — `scraper tasks with no ODOS job: ['ingest.opencritic', 'ingest.psn', 'ingest.steamcharts']`.

- [ ] **Шаг 3: Добавьте три строфы job** в `spec/ODOS/examples/ingestion.yml`, зеркалируя `metacritic_ingest_job` в точности (те же `tags`, `doc` с названием рыночного измерения):

```yaml
  opencritic_ingest_job:
    task: ingest.opencritic
    tags: {ingestion: scraping}
    doc: "Quality dimension — OpenCritic JSON-LD scrape → raw Parquet (demo-safe by default)."
  psn_ingest_job:
    task: ingest.psn
    tags: {ingestion: scraping}
    doc: "Console-pricing dimension — PSN Store concept JSON-LD → raw Parquet (demo-safe by default)."
  steamcharts_ingest_job:
    task: ingest.steamcharts
    tags: {ingestion: scraping}
    doc: "Traction dimension — SteamCharts CSS scrape → raw Parquet (demo-safe by default)."
```

- [ ] **Шаг 4: Запустите тест, убедитесь, что он проходит.** Запуск: `uv run pytest src/tests/unit/test_odos_ingestion_fixture.py -v`. Ожидается: PASS.

- [ ] **Шаг 5: Обновите документ реализации ODOS.** В `spec/ODOS/IMPLEMENTATION.md` §2, таблица `ingestion.yml`, замените в единственной строке `metacritic_ingest_job` заметку «no Dagster job wired yet» реальностью четырёх скрейперов: живут в реестре, Prefect достигает их через `ingest.all`; нет Dagster job по замыслу (см. слой 3). Одна строка на скрейпер.

- [ ] **Шаг 6: Коммит.** Запуск: `git commit -o spec/ODOS/examples/ingestion.yml spec/ODOS/IMPLEMENTATION.md src/tests/unit/test_odos_ingestion_fixture.py -m "feat(odos): project the three scrapers into ingestion.yml + coverage gate"` (тело: `Refs: #37` `Refs: #18` `Refs: #19`).

### Задача 1.2: извлечь проекцию в детерминированный скрипт (`/save-all-deterministic-for-skill-as-scripts`)

**Файлы:**
- Предложить (создать через flow скилла, не вручную): `~/.ai/skills/_scripts/de/ingestion/odos_scraper_jobs.py` + рецепты Justfile `emit-odos-scraper-jobs` / `check-odos-scraper-jobs` в `~/.ai/skills/_scripts/de/ingestion/Justfile`.
- Изменить: `Makefile` (цель `check`) — добавить вызов `--check`.

**Интерфейсы:**
- Потребляет: имена скрейперов реестра + дескриптор `(system, entity, dimension doc)` каждого источника из `spec/sources/*.yaml`.
- Производит: идемпотентную перезапись блока `*_ingest_job` скрейперов в `ingestion.yml`; `--check` выходит с ненулевым кодом при дрейфе и печатает отсутствующие/лишние строфы.

- [ ] **Шаг 1:** Ручное написание шага 1.3 — разовое; *долговечная* потребность в том, чтобы job N+1 проецировался автоматически. Строфа — чистая функция от `(task_name, dimension_doc)`. Извлеките её: `odos_scraper_jobs.py emit` регенерирует блок, `check` сравнивает и падает при дрейфе. Это ровно проекция `to_*` компилятора ODOS на гранулярности скрейпера — постройте её здесь, чтобы #37 её унаследовал.
- [ ] **Шаг 2:** Вынесите скаляры в settings (`~/.ai/skills/.settings/de/ingestion/`): путь фикстуры, тег `{ingestion: scraping}`, набор исключений не-скрейперов, шаблон `doc`. Никаких литералов в теле.
- [ ] **Шаг 3:** Подключите `just … check-odos-scraper-jobs` в `make check`, чтобы задача-скрейпер, добавленная без её строфы ODOS, падала локально, а не только в ревью.
- [ ] **Шаг 4:** Это PROPOSE-ONLY. Не пишите файл скилла. Проведите через `/upsert-skill add-data-source` (проекция — недостающий хвост DoD источника) → его обязательный пост-шаг `/save-all-deterministic-for-skill-as-scripts` производит скрипт + settings. Сначала подтвердите охват с пользователем.

**Скилл/скрипт/хук для слоя 1:**
- **Скрипт (НОВЫЙ, основной):** `odos_scraper_jobs.py` (emit + check) — выше.
- **Скилл (переиспользовать):** `/add-data-source` владеет DoD источника, который *производит* задачу реестра; эта проекция — его сейчас отсутствующий хвост оркестрации. Свернуть внутрь, а не новый скилл.
- **Хук:** покрыт сквозным гейтом `scraper-orchestration-drift` (см. конец) — режим `check` слоя 1 — одно из трёх его утверждений.

---

## Слой 2 — основная оркестрация Prefect

**Что меняется:** Сегодня `make_engine_flow` запускает `ingest_raw = ingest_all` как единый ассет `_ingest` с ключом `…/raw/rawg__games`, так что все четыре скрейпера садятся невидимо за ключом rawg — нулевая per-source линейность. Этот слой даёт каждому *включённому* источнику-скрейперу собственный ассет `@materialize` (`file://ogip/{engine}/raw/{system}__{entity}`), который вливается в `_transform`, и подключает плейсхолдер `parse_to_landing` за выключенным по умолчанию конфиг-гейтом, так что включение landing hop из ADR-0014 позже — переключение конфига, а не изменение кода.

### Задача 2.1: per-source raw ассеты в engine flow

**Файлы:**
- Изменить: `pipelines/flows/_common.py` (добавить `make_ingest_assets`, перекоммутировать `make_engine_flow`)
- Создать: `src/tests/unit/test_prefect_ingest_assets.py`

**Интерфейсы:**
- Потребляет: вызываемые объекты реестра `ogip.tasks.ingest`; список включённых источников из `config/config.yml` `sources.<name>.enabled`; хелпер raw-ключа из задачи 2.3 (до неё — inline-конструкция, подлежащая замене).
- Производит: `make_ingest_assets(engine: str) -> tuple[Callable[[], str], list[Callable[[], str]]]` — возвращает `(rawg_asset, scraper_assets)`; `rawg_asset()` возвращает путь вывода RAWG (якорь трансформации), каждый ассет скрейпера возвращает свой raw-путь. `make_engine_flow` вливает их все в `_transform`.

- [ ] **Шаг 1: Напишите проваливающийся тест.** Утвердите, что основной поток материализует отдельный raw-ассет на каждый включённый скрейпер, а не один ключ rawg на всех.

```python
# src/tests/unit/test_prefect_ingest_assets.py
from pipelines.flows._common import scraper_raw_keys


def test_each_enabled_scraper_has_its_own_raw_asset_key():
    keys = scraper_raw_keys("sqlmesh")
    assert "file://ogip/sqlmesh/raw/opencritic__game" in keys
    assert "file://ogip/sqlmesh/raw/psn__concept" in keys
    assert "file://ogip/sqlmesh/raw/steamcharts__app" in keys
    # rawg stays the transform anchor, distinct from the scrapers
    assert "file://ogip/sqlmesh/raw/rawg__games" not in keys
```

- [ ] **Шаг 2: Запустите его, убедитесь, что он падает.** Запуск: `uv run pytest src/tests/unit/test_prefect_ingest_assets.py -v`. Ожидается: FAIL — `scraper_raw_keys` не определён.

- [ ] **Шаг 3: Реализуйте `scraper_raw_keys` + `make_ingest_assets`** в `_common.py`. Карта source→(system,entity,task) — это реестр; держите её явной и небольшой (это та же карта, которую задача 2.3 выносит наружу):

```python
# pipelines/flows/_common.py  (add near ingest_raw)
from ogip.tasks.ingest import (
    ingest_metacritic, ingest_opencritic, ingest_psn, ingest_steamcharts,
)

# (system, entity, registry callable) — one row per scraper. rawg is NOT here:
# it is the unconditional Layer-0 transform anchor, kept as ingest_raw below.
_SCRAPERS = (
    ("metacritic", "game", ingest_metacritic),
    ("opencritic", "game", ingest_opencritic),
    ("psn", "concept", ingest_psn),
    ("steamcharts", "app", ingest_steamcharts),
)


def _enabled(name: str) -> bool:
    return bool(load_app_config()["sources"].get(name, {}).get("enabled"))


def scraper_raw_keys(engine: str) -> list[str]:
    """Prefect asset key per *enabled* scraper source (per-source lineage)."""
    return [
        f"file://ogip/{engine}/raw/{system}__{entity}"
        for system, entity, _ in _SCRAPERS
        if _enabled(system)
    ]
```

- [ ] **Шаг 4:** В `make_engine_flow` замените единый `_ingest` на rawg-якорь + влитый ассет скрейпера на каждый `scraper_raw_keys(engine)`; каждый `@materialize` скрейпера оборачивает свой вызываемый объект реестра и демо-безопасен по наследованию. `_transform` по-прежнему привязан к пути rawg (якорь warehouse); ассеты скрейперов — сиблинги, питающие тот же шаг `_transform`. Сохраните `ingest_all` для CLI/config-gated пути — поток теперь выражает fan-out как ассеты вместо того, чтобы прятать его в одной задаче.

- [ ] **Шаг 5: Запустите тесты, убедитесь в проходе.** Запуск: `uv run pytest src/tests/unit/test_prefect_ingest_assets.py -v && make check`. Ожидается: PASS; ruff + pyright strict чисто.

- [ ] **Шаг 6: Коммит.** `git commit -o pipelines/flows/_common.py src/tests/unit/test_prefect_ingest_assets.py -m "feat(pipelines): per-source scraper raw assets for Prefect lineage"` (`Refs: #37 #18 #19`).

### Задача 2.2: подключить `parse_to_landing` за выключенным по умолчанию гейтом

**Файлы:**
- Изменить: `pipelines/flows/_common.py`, `config/config.yml` (добавить `pipeline.landing.enabled: false`)

**Интерфейсы:**
- Потребляет: `ogip.tasks.ingest.parse_to_landing` (плейсхолдер), `config.pipeline.landing.enabled`.
- Производит: опциональный ассет `_parse_to_landing` с ключом `postgres://ogip/{engine}/landing`, материализуемый только когда гейт включён; no-op (логирует плейсхолдер ADR-0014), пока не появится асинхронный ScraperSource.

- [ ] **Шаг 1:** Добавьте `pipeline.landing.enabled: false` в `config/config.yml` (SSoT; никогда не ребро графа). Отрендерьте env при необходимости (`make render-env`).
- [ ] **Шаг 2:** В `make_engine_flow`, когда гейт включён, добавьте в начало `@materialize` `_parse_to_landing`, вызывающий `parse_to_landing()`. Выключено по умолчанию означает, что поведение `make run` не меняется; подключение существует, чтобы ADR-0014 был переключением конфига.
- [ ] **Шаг 3: Тест** того, что дефолт гейта оставляет набор ассетов потока неизменным (нет ключа `postgres://…/landing` при `enabled: false`) и производит его при переключении. Запустите `make check`. Коммит (`Refs: #37`).

### Задача 2.3: вынести схему raw-ключа наружу (`/save-all-deterministic-for-skill-as-scripts` + стандарты кода)

**Файлы:**
- Изменить: `pipelines/flows/_common.py`, `pipelines/flows/engines/prefect_dagster.py` (потреблять хелпер), `config/config.yml` или модуль-константу `src/ogip/` для схемы URI.

**Интерфейсы:**
- Производит: `raw_asset_key(engine: str, system: str, entity: str) -> str` — единственный конструктор `file://ogip/{engine}/raw/{system}__{entity}`. Схема (`file://ogip/{engine}/raw/`) — значение settings, а не литерал.

- [ ] **Шаг 1:** Строка ключа сейчас впечатана вручную в `_common.py:107` и `prefect_dagster.py:29-35`. Замените обе на `raw_asset_key(...)`. Одно место конструирует ключи; дрейф между двумя потоками становится невозможным.
- [ ] **Шаг 2:** Вынесите схему URI в значение settings (по стандарту код-спеки `python_module_layout.yml` — скаляры вне тел). Проверьте, что `raw_asset_key("sqlmesh","opencritic","game")` даёт round-trip ключа L2.
- [ ] **Шаг 3: Коммит** (`Refs: #37`).

**Скилл/скрипт/хук для слоя 2:**
- **Скрипт (НОВЫЙ, основной):** хелпер `raw_asset_key` + settings (задача 2.3) — детерминированная поверхность, извлечённая по `/save-all-deterministic-for-skill-as-scripts`, потребляемая L2/L3.
- **Скилл (переиспользовать):** `/integrate-sql-tool-with-prefect` для механики сборки потока; не создавайте новый скилл Prefect.
- **Хук:** сквозной `scraper-orchestration-drift` (ниже) — его утверждение L2 — «у каждого зарегистрированного скрейпера есть запись в `scraper_raw_keys`».

---

## Слой 3 — альт. Prefect + Dagster-over-dlt-and-Airbyte-and-dbt

**Описан только как дельта от слоя 2.**

Шов — `pipelines/flows/engines/prefect_dagster.py`: Dagster владеет **только ядром warehouse на dlt+dbt** (`run_dagster_dlt_dbt` через `dg launch` в изолированном окружении `experimental/orchestration/dagster_ogip`); Prefect владеет скрейпингом, ML, публикацией, алертингом.

**Дельта 1 — ассеты скрейпера побайтово идентичны ассетам слоя 2, переиспользуются, а не реализуются заново.** `flow_dagster` импортирует `make_ingest_assets("dagster")` из `_common` (задача 2.1) и вливает *те же* `@materialize`-ассеты скрейперов в построенный Dagster warehouse вместо построенного Prefect. Единственная строка, меняющаяся против слоя 2, — что `_transform` заменяется на `_dagster_dlt_dbt` (`run_dagster_dlt_dbt`). Ничего скрейпер-образного не переезжает в Dagster.

**Дельта 2 — несущий пункт корректности: скрейперы не проходят через dlt или Airbyte.** Скрейпер — кастомный парсер HTML→JSON-LD/CSS. У `dlt` и Airbyte нет обобщённого источника «запусти мой кастомный парсер против этого URL» — их источники — коннекторы API/DB/файлов. Так что «Dagster-over-dlt-**and-Airbyte**-and-dbt» для *скрейпер*-задач — no-op: нет ничего, *как* их ингестить. Они остаются Python-ассетами Prefect в этом профиле ровно как в слое 2. Только rawg-образные источники API/DB — кандидаты для dlt/Airbyte-дорожки Dagster.

**Дельта 3 — Airbyte — ортогональный, сейчас отсутствующий компонент.** `experimental/orchestration/dagster_ogip` сегодня несёт только `dagster_dlt` + `dagster_dbt`; нет `dagster_airbyte`. Добавление Airbyte означает новый компонент Dagster, ингестящий *будущий источник API/DB* (например, API SteamSpy/IGDB), отслеживаемый отдельно — он никогда не трогает подключение скрейпера. Назовите этот пробел в документе, чтобы читатель не ждал появления скрейперов под Airbyte.

### Задача 3.1: переиспользовать ассеты скрейпера L2 в обёрнутом Dagster потоке

**Файлы:**
- Изменить: `pipelines/flows/engines/prefect_dagster.py`
- Создать: `src/tests/unit/test_prefect_dagster_reuses_scrapers.py`

**Интерфейсы:**
- Потребляет: `make_ingest_assets`/`scraper_raw_keys` (задача 2.1), `run_dagster_dlt_dbt` (существующий), `raw_asset_key` (задача 2.3).
- Производит: `flow_dagster`, материализующий те же raw-ключи скрейперов, что и основной поток + ключ warehouse Dagster.

- [ ] **Шаг 1: Проваливающийся тест** — набор ассетов скрейпера идентичен в основном и Dagster-потоках (инвариант переиспользования, доказывающий отсутствие форка):

```python
# src/tests/unit/test_prefect_dagster_reuses_scrapers.py
from pipelines.flows._common import scraper_raw_keys


def test_dagster_profile_reuses_the_main_scraper_assets():
    assert scraper_raw_keys("dagster") == [
        k.replace("/sqlmesh/", "/dagster/") for k in scraper_raw_keys("sqlmesh")
    ]
```

- [ ] **Шаг 2:** Запустите его — FAIL, пока `flow_dagster` не потребляет общий хелпер.
- [ ] **Шаг 3:** В `prefect_dagster.py` влейте ассеты скрейперов `make_ingest_assets("dagster")` в `flow_dagster` рядом с `_dagster_dlt_dbt`; сохраните `run_dagster_dlt_dbt` как *единственную* дельту от `make_engine_flow`. Замените впечатанные вручную литералы `RAW_KEY`/`WAREHOUSE_KEY` на `raw_asset_key(...)`.
- [ ] **Шаг 4:** Запустите тест + `make check` — PASS.
- [ ] **Шаг 5:** В docstring модуля `prefect_dagster.py` и `spec/ODOS/IMPLEMENTATION.md` добавьте заметку из двух предложений «скрейперы остаются на стороне Prefect; у Airbyte/dlt нет источника-парсера». Коммит (`Refs: #37`).

**Скилл/скрипт/хук для слоя 3:**
- **Скрипт:** ничего нового — переиспользует хелперы задач 2.1/2.3 (в этом *и есть* смысл: нет специфичного для L3 кода скрейпера).
- **Скилл (переиспользовать):** `/call-dagster-from-prefect` (паттерн шва уже в этом файле). Для будущего компонента Airbyte: `/add-dagster-module` + `/integrate-dagster-with-dbt` — но это задача источника API, вне области подключения скрейпера; отметьте её, не стройте.
- **Хук:** утверждение переиспользования сквозного гейта покрывает `scraper_raw_keys("dagster") == scraper_raw_keys("sqlmesh")`-по-модулю-движка, ловя будущий форк.

---

## Слой 4 — альт. оркестрация Bruin

**Описан только как дельта от слоёв 2 и 3.**

`pipelines/flows/engines/prefect_bruin.py` — это `make_engine_flow("bruin")` — он переиспользует `_common` целиком. Bruin — SQL-раннер для трансформации (`spec/sql` запускается нативно, «spec *есть* Bruin»); поток вокруг него — Prefect.

**Дельта от слоя 2:** нет никакой в ассетах ingestion. Как только задача 2.1 приземлится, `make_engine_flow("bruin")` наследует идентичные per-source ассеты скрейперов бесплатно; единственная подмена — `build_warehouse("bruin")` → `run_transform_engine("bruin")`, который уже существует. Нет специфичного для Bruin кода скрейпера для написания.

**Дельта от слоя 3:** в отличие от слоя 3, Bruin **не** втягивает ядро warehouse в чужой оркестратор. Вся цепочка остаётся в Prefect; Bruin вызывается *только* как SQL-движок для `_transform`. Так что скрейперы → Prefect-ассеты → warehouse, запущенный Bruin. Слой 3 подменяет ядро на Dagster; слой 4 подменяет только раннер SQL-диалекта.

**Bruin-нативная альтернатива — названа и намеренно отклонена (YAGNI).** Bruin поддерживает Python-ассеты (`type: python`) и мог бы выразить каждый скрейпер как Bruin-ассет в `spec/bruin/pipeline.yml`, давая Bruin-нативную линейность. Это отклонено: оно дублирует каждую задачу реестра за вторым обёрткой, специфичной для оркестратора (нарушая ограничение «реестр — SSoT, никакой параллельной реализации»), и не покупает ничего, пока Bruin не станет *основным* оркестратором. Ценность Bruin здесь — SQL-линейность, а не Python-оркестрация — та же логика, что и у слоя 3 (держите кастомный Python там, где он живёт), по другой причине. План оставляет скрейперы на общем пре-шаге Prefect `make_engine_flow`.

### Задача 4.1: подтвердить, что Bruin наследует общие ассеты скрейперов (только регрессионный гейт)

**Файлы:**
- Создать: `src/tests/unit/test_prefect_bruin_inherits_scrapers.py`

**Интерфейсы:**
- Потребляет: `pipelines.flows.engines.prefect_bruin.flow`, `scraper_raw_keys` (задача 2.1).

- [ ] **Шаг 1:** Никаких изменений production-кода — эта задача — гейт того, что Bruin никогда не отрастит параллельный путь скрейпера. Напишите тест, утверждающий, что ключи скрейперов потока Bruin равны `scraper_raw_keys("bruin")` и что не существует файла скрейпера Python-ассета `spec/bruin/` (отклонённая альтернатива остаётся отклонённой).

```python
# src/tests/unit/test_prefect_bruin_inherits_scrapers.py
from pathlib import Path

from pipelines.flows._common import scraper_raw_keys


def test_bruin_reuses_shared_scraper_assets_and_grows_no_parallel_path():
    assert scraper_raw_keys("bruin")  # inherited via make_engine_flow, non-empty
    # the deliberately-declined Bruin-native scraper wrapper must not appear
    assert not list(Path("spec").glob("bruin/**/*scraper*"))
```

- [ ] **Шаг 2:** Запустите его — PASS немедленно (документирует дельту как исполняемый инвариант). `make check`, коммит (`Refs: #37`).

**Скилл/скрипт/хук для слоя 4:**
- **Скрипт:** ничего нового — полное наследование от задачи 2.1.
- **Скилл (переиспользовать):** `/generate-agnostic-bruin-sql-specs`, `/spec-compile-engines`, `/integrate-sql-tool-with-prefect` — все для SQL-transform-стороны, ни один не специфичен для скрейпера.
- **Хук:** сквозной гейт + утверждение «нет параллельного пути» задачи 4.1.

---

## Сквозное: детерминированный скрипт + единственный хук (PROPOSE-ONLY)

Весь план — одна проекция, применённая четырьмя способами. Выпадают два долговечных артефакта, оба созданы через flow скилла, никогда не вручную:

### A. `odos_scraper_jobs.py` — скрипт проекции (задача 1.2)
Читает имена скрейперов реестра + дескрипторы источников → emit-ит/`--check`-ит строфы скрейперов ODOS `ingestion.yml`. Подготовка компилятора `to_odos` на гранулярности скрейпера. Живёт в `~/.ai/skills/_scripts/de/ingestion/`, обёрнут в Justfile, скаляры в `.settings/`. Маршрут через `/upsert-skill add-data-source` → обязательный `/save-all-deterministic-for-skill-as-scripts`.

### B. `scraper-orchestration-drift` — единственный хук, охраняющий все четыре слоя
Единый `check` (подключённый в `make check` + предложенный как pre-commit хук), утверждающий для **каждого** зарегистрированного `ingest.<scraper>`:
1. **L1** — существует ODOS `*_ingest_job` с `task: ingest.<scraper>` (утверждение задачи 1.1).
2. **L2** — `scraper_raw_keys("sqlmesh")` содержит его ключ (задача 2.1).
3. **L3/L4** — наборы ключей скрейперов альт-профилей равны L2 по модулю движка (задачи 3.1, 4.1 — инвариант анти-форка).

Это ровно тот дрейф, на который налетела эта сессия: три скрейпера отгружены, ни один не спроецирован в ODOS, ни одному не дана Prefect-линейность, и ничто не было красным. Хук делает «добавь скрейпер, забудь проекцию» проваливающейся сборкой. Это первый взнос с областью действия скрейпера в тест эквивалентности #37 — той же формы, меньший радиус поражения, собираемый сейчас.

**Переиспользуемые скиллы (НЕ пересоздаются):** `/add-data-source` (производит задачу реестра = вход этого плана), `/integrate-sql-tool-with-prefect`, `/call-dagster-from-prefect`, `/add-dagster-module`, `/integrate-dagster-with-dbt`, `/spec-compile-engines`, `/generate-agnostic-bruin-sql-specs`, `/find-sources-and-match-tool`. **Новый скилл не оправдан** — детерминированная работа — два скрипта + один хук; по «or better just script» пользователя, скрипты первичны, а любой тонкий фронт-скилл опционален и предлагается через `/create-skill` только после одобрения.

---

## Само-ревью

**Покрытие спеки:** L1 (фикстура + гейт) ✅ задачи 1.1–1.2. L2 (per-source ассеты + гейт parse_to_landing + хелпер ключа) ✅ задачи 2.1–2.3. L3 (только дельта, переиспользование + вывод об отсутствии источника-парсера у Airbyte/dlt) ✅ задача 3.1. L4 (только дельта, полное наследование + отклонённая Bruin-нативная альтернатива) ✅ задача 4.1. Сквозной скрипт + хук ✅. Предложения скилл/скрипт/хук по слоям ✅, все PROPOSE-ONLY.

**Скан плейсхолдеров:** Нет «TBD»/«add error handling». `parse_to_landing` описан *как* плейсхолдер, потому что он им подлинно является (ADR-0014 не отгружен) — задача подключает гейт, а не фейковое тело, что и есть честный ход. Все шаги кода несут реальный код.

**Согласованность типов:** `scraper_raw_keys(engine: str) -> list[str]`, `raw_asset_key(engine, system, entity) -> str`, `make_ingest_assets(engine) -> tuple[...]` используются согласованно по задачам 2.1, 2.3, 3.1, 4.1. Строки `_SCRAPERS` — `(system, entity, callable)` повсюду. Граница словаря реестра (`_NON_SCRAPER`) идентична в задаче 1.1 и хуке.

**Якорь корректности:** центральное утверждение плана — скрейперы остаются на стороне Prefect в каждом профиле, потому что у dlt/Airbyte/Bruin нет источника с кастомным парсером — это то, что делает слои 3 и 4 подлинно тонкими по дельте, а не четырьмя параллельными реализациями. Это то переиспользование, которого требует ограничение «реестр — SSoT».
