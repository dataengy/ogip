<!-- ru-translation-of: docs/superpowers/plans/2026-07-20-odos-task-registry.md sha:a2709e8450a3 -->
<!-- Автоперевод. Источник — docs/superpowers/plans/2026-07-20-odos-task-registry.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [2026-07-20-odos-task-registry.md](2026-07-20-odos-task-registry.md)

# План реализации реестра задач ODOS

> **Для agentic-исполнителей:** ОБЯЗАТЕЛЬНЫЙ SUB-SKILL: используйте superpowers:subagent-driven-development (рекомендуется) или superpowers:executing-plans, чтобы реализовывать этот план задача-за-задачей. Шаги используют синтаксис чекбоксов (`- [ ]`) для отслеживания.

**Цель:** Построить `src/ogip/tasks/` — единый реестр типизированных Python-функций задач — и провести через него
и `jobs/dg-tasks.sh` (Dagster), и `pipelines/flows/_common.py` (Prefect), чтобы две
линии оркестраторов перестали расходиться.

**Архитектура:** Реестр имя → callable (`@odos_task("dbt.build")`) плюс CLI `python -m
ogip.tasks`. Тела задач — простые типизированные функции без импорта оркестратора, так что Dagster
оборачивает их в `@op`, а Prefect в `@task`, при этом ни один из них не владеет логикой. Это план 1 из 3
для ODOS ([проектирование](../specs/2026-07-20-odos-orchestration-spec-design.md) §5); он поставляется и окупает
себя без какого-либо ODOS YAML, без IR и без компилятора в существовании пока что.

**Технологический стек:** Python 3.13, uv, pytest, pyright strict, ruff, loguru (`log`), dbt-core через
`uv run --group engines`.

## Глобальные ограничения

- Логирование: `from ogip.logger import log`, вызывайте `log.info(...)`. Никогда `logger.` (правило 4 AGENTS.md).
- Pyright **strict**, 0 ошибок. Ruff чист. `make check` — это гейт.
- Runtime-окружение: `UV_PROJECT_ENVIRONMENT=.run/venv`, экспортируется build-файлами.
- `spec/` — это SSoT — dbt-проект генерируется через `compile_to_dbt`, никогда не редактируется вручную.
- Каждый коммит несёт `Refs: #37` (форсируется через `.ci/steps/commit-binding.sh`).
- Работайте в этой линии: `bash src/scripts/lane.sh acquire orchestration "<reason>"` перед записью.
- Никакого `from __future__ import annotations` в файлах, которые импортирует Dagster (он стрингизует аннотацию
  op-контекста, а проверка типизированного контекста Dagster её отвергает). Файлы реестра не импортируются
  Dagster напрямую — CLI является границей — поэтому они могут его использовать.

## Два решения, которые фиксирует этот план

Оба — открытые вопросы в проектировании; план разрешает их и объясняет почему.

**1. `ensure_raw` исчезает (проектирование §13.2).** Сегодня `dg-tasks.sh:build-dwh` тихо ингестит сырые
данные, когда parquet отсутствует; линия Prefect ингестит безусловно отдельным шагом. Ни одно из этого
не становится дефолтом реестра: **`dbt.build` вообще не касается ингеста.** Build, который
тайно ингестит, — это скрытое ребро в графе зависимостей, а весь тезис ODOS в том, что
зависимости живут в spec (`select:`, композиция job'ов), а не зарыты в телах задач. Вызывающие,
которым нужно сырое первым, компонуют `ingest.rawg` перед `dbt.build`.

**2. `project_dir` остаётся аргументом вызывающего.** `transform/dbt/` (закоммичен, запускается из корня репозитория
через `uv run --group engines dbt`) и `experimental/orchestration/dagster_ogip/dbt/` (генерируется в
рантайме, запускается через `uv run dbt` в venv Dagster) — это два проекта, построенных из одного spec. Этот план
унифицирует **путь кода и флаги** — одна функция, один стиль вызова — оставляя
местоположение параметром. Консолидация двух директорий — реальный follow-up, но она изменила бы
обвязку `DbtProjectComponent` из ADR-0015, что вне области здесь.

## Структура файлов

| Файл | Ответственность |
|---|---|
| `src/ogip/tasks/_registry.py` | карта имя → callable, `@odos_task`, поиск, ошибки. Никакой логики задач. |
| `src/ogip/tasks/__init__.py` | ре-экспорт API реестра; импорт модулей задач для регистрации |
| `src/ogip/tasks/dbt.py` | `dbt.build` · `dbt.parse` · `dbt.deps` — regenerate-from-spec + вызов dbt |
| `src/ogip/tasks/ingest.py` | `ingest.rawg` · `ingest.parse_to_landing` |
| `src/ogip/tasks/cdc.py` | `cdc.catchup` |
| `src/ogip/tasks/snapshots.py` | `snapshot.write` |
| `src/ogip/tasks/integrations.py` | `integrations.trigger_prefect` |
| `src/ogip/tasks/__main__.py` | `python -m ogip.tasks <name> [--k=v]` — граница шелла |
| `src/tests/unit/test_tasks_registry.py` | семантика реестра + CLI |
| `src/tests/unit/test_tasks_dbt.py` | конструирование команды dbt (без выполнения dbt) |

Реестр живёт в `_registry.py`, а не в `__init__.py`, чтобы модули задач могли импортировать
`odos_task` без циклического импорта обратно через пакетный `__init__`.

---

### Задача 1: Ядро реестра

**Файлы:**
- Создать: `src/ogip/tasks/_registry.py`
- Создать: `src/ogip/tasks/__init__.py`
- Тест: `src/tests/unit/test_tasks_registry.py`

**Интерфейсы:**
- Потребляет: ничего.
- Производит: `odos_task(name: str) -> Callable[[F], F]` · `get_task(name: str) -> Callable[..., object]` ·
  `task_names() -> list[str]` · `TASKS: dict[str, Callable[..., object]]` ·
  `TaskNotFoundError(KeyError)` · `DuplicateTaskError(RuntimeError)`.

- [ ] **Шаг 1: Напишите падающий тест**

Создайте `src/tests/unit/test_tasks_registry.py`:

```python
"""Registry semantics: registration, lookup, and the two failure modes that must be loud."""

import pytest

from ogip.tasks import (
    TASKS,
    DuplicateTaskError,
    TaskNotFoundError,
    get_task,
    odos_task,
    task_names,
)


@pytest.fixture(autouse=True)
def _restore_registry():
    """Tests here register probe tasks into the module-global registry.

    Without this, a second run in the same process (pytest --lf, xdist reruns) hits
    DuplicateTaskError on a name a previous test left behind, and later tests see probe
    entries in the project vocabulary. Snapshot and restore around every test.
    """
    saved = dict(TASKS)
    yield
    TASKS.clear()
    TASKS.update(saved)


def test_registered_task_is_retrievable_by_name():
    @odos_task("probe.echo")
    def _echo(value: str) -> str:
        return value

    assert get_task("probe.echo")("hi") == "hi"
    assert "probe.echo" in task_names()


def test_unknown_name_raises_with_the_known_names_listed():
    with pytest.raises(TaskNotFoundError) as excinfo:
        get_task("probe.nope")
    assert "probe.nope" in str(excinfo.value)


def test_duplicate_registration_is_rejected():
    @odos_task("probe.dup")
    def _first() -> None: ...

    with pytest.raises(DuplicateTaskError):

        @odos_task("probe.dup")
        def _second() -> None: ...


def test_task_names_is_sorted():
    assert task_names() == sorted(task_names())
```

- [ ] **Шаг 2: Запустите тест, чтобы убедиться, что он падает**

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run pytest src/tests/unit/test_tasks_registry.py -v`
Ожидается: FAIL — `ModuleNotFoundError: No module named 'ogip.tasks'`

- [ ] **Шаг 3: Напишите минимальную реализацию**

Создайте `src/ogip/tasks/_registry.py`:

```python
"""The ODOS task registry — a closed vocabulary of orchestrator-agnostic callables.

A task is a plain typed function. It imports no orchestrator, so Dagster can wrap it in an
`@op` and Prefect in a `@task` without either owning the behaviour. Names are the contract:
ODOS specs address tasks by registry name, and the compiler validates the name at compile
time rather than letting a bad reference surface at runtime.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

__all__ = [
    "TASKS",
    "DuplicateTaskError",
    "TaskNotFoundError",
    "get_task",
    "odos_task",
    "task_names",
]


class TaskNotFoundError(KeyError):
    """No task is registered under that name."""


class DuplicateTaskError(RuntimeError):
    """Two functions claimed the same registry name."""


TASKS: dict[str, Callable[..., object]] = {}

F = TypeVar("F", bound=Callable[..., object])


def odos_task(name: str) -> Callable[[F], F]:
    """Register ``fn`` under ``name``. Duplicate names are a bug, not a last-one-wins."""

    def register(fn: F) -> F:
        if name in TASKS:
            raise DuplicateTaskError(f"task {name!r} is already registered")
        TASKS[name] = fn
        return fn

    return register


def get_task(name: str) -> Callable[..., object]:
    """Look up a task, listing the vocabulary when the name is wrong."""
    try:
        return TASKS[name]
    except KeyError:
        raise TaskNotFoundError(f"unknown task {name!r}; known: {', '.join(task_names())}") from None


def task_names() -> list[str]:
    return sorted(TASKS)
```

Создайте `src/ogip/tasks/__init__.py`:

```python
"""ODOS task registry — see `_registry` for the contract, the sibling modules for the tasks."""

from ogip.tasks._registry import (
    TASKS,
    DuplicateTaskError,
    TaskNotFoundError,
    get_task,
    odos_task,
    task_names,
)

__all__ = [
    "TASKS",
    "DuplicateTaskError",
    "TaskNotFoundError",
    "get_task",
    "odos_task",
    "task_names",
]
```

- [ ] **Шаг 4: Запустите тест, чтобы убедиться, что он проходит**

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run pytest src/tests/unit/test_tasks_registry.py -v`
Ожидается: PASS, 4 теста

- [ ] **Шаг 5: Проверьте гейты**

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run ruff check src/ogip/tasks src/tests/unit/test_tasks_registry.py && UV_PROJECT_ENVIRONMENT=.run/venv uv run pyright src/ogip/tasks`
Ожидается: ruff чист; pyright `0 errors`

- [ ] **Шаг 6: Коммит**

```bash
git add src/ogip/tasks/_registry.py src/ogip/tasks/__init__.py src/tests/unit/test_tasks_registry.py
git commit -m "feat(tasks): ODOS task registry core

Refs: #37"
```

---

### Задача 2: Задачи dbt

**Файлы:**
- Создать: `src/ogip/tasks/dbt.py`
- Изменить: `src/ogip/tasks/__init__.py` (добавить импорт регистрации)
- Тест: `src/tests/unit/test_tasks_dbt.py`

**Интерфейсы:**
- Потребляет: `odos_task` из Задачи 1; `compile_to_dbt(spec_sql_dir, project_dir, *, warehouse, repo_root, with_packages=True) -> list[str]` из `ogip.spec_compile.to_dbt`.
- Производит: `dbt_build(*, project_dir: Path, full_refresh: bool = False, select: str | None = None, state: str | None = None) -> None` ·
  `dbt_parse(*, project_dir: Path) -> None` · `dbt_deps(*, project_dir: Path) -> None` ·
  `dbt_command(project_dir: Path, verb: str, *flags: str) -> list[str]` (экспортируется для тестирования).

Имена в реестре: `dbt.build`, `dbt.parse`, `dbt.deps`.

- [ ] **Шаг 1: Напишите падающий тест**

Создайте `src/tests/unit/test_tasks_dbt.py`:

```python
"""dbt task command construction.

These assert the argv the registry builds, not dbt's behaviour — running dbt belongs to the
integration/e2e tiers. The point is that ONE code path serves both orchestrators, so the flags
are pinned here where a regression is cheap to see.
"""

from pathlib import Path

from ogip.tasks.dbt import dbt_command

PROJECT = Path("transform/dbt")


def test_build_places_project_flags_after_the_subcommand():
    argv = dbt_command(PROJECT, "build")
    assert argv[:5] == ["uv", "run", "--group", "engines", "dbt"]
    assert argv[5] == "build"
    assert "--project-dir" in argv
    # dbt rejects --project-dir before the subcommand; the verb must come first.
    assert argv.index("build") < argv.index("--project-dir")


def test_extra_flags_are_appended_after_the_project_flags():
    argv = dbt_command(PROJECT, "build", "--full-refresh")
    assert argv[-1] == "--full-refresh"


def test_project_and_profiles_dirs_both_point_at_the_project():
    argv = dbt_command(PROJECT, "parse")
    assert argv[argv.index("--project-dir") + 1] == str(PROJECT)
    assert argv[argv.index("--profiles-dir") + 1] == str(PROJECT)
```

- [ ] **Шаг 2: Запустите тест, чтобы убедиться, что он падает**

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run pytest src/tests/unit/test_tasks_dbt.py -v`
Ожидается: FAIL — `ModuleNotFoundError: No module named 'ogip.tasks.dbt'`

- [ ] **Шаг 3: Напишите минимальную реализацию**

Создайте `src/ogip/tasks/dbt.py`:

```python
"""dbt tasks — regenerate the project from `spec/`, then invoke dbt.

Regeneration is implicit and unconditional: `spec/` is the SSoT (ADR-0005) and the dbt project
is generated, never hand-edited, so a caller that had to *ask* for regeneration would be
asserting a fact the system already owns.

These tasks deliberately do NOT ensure raw data exists. A build that silently ingests is a
hidden edge in the dependency graph; ingestion is `ingest.rawg`, composed ahead of the build by
whoever needs it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ogip.config import get_settings
from ogip.logger import log
from ogip.spec_compile.to_dbt import compile_to_dbt
from ogip.tasks._registry import odos_task

__all__ = ["dbt_build", "dbt_command", "dbt_deps", "dbt_parse"]

_REPO = Path(__file__).resolve().parents[3]
_SPEC_SQL = _REPO / "spec" / "sql"


def dbt_command(project_dir: Path, verb: str, *flags: str) -> list[str]:
    """Build the dbt argv. `--project-dir`/`--profiles-dir` must follow the subcommand."""
    return [
        "uv", "run", "--group", "engines", "dbt", verb,
        "--project-dir", str(project_dir),
        "--profiles-dir", str(project_dir),
        *flags,
    ]


def _regenerate(project_dir: Path) -> list[str]:
    models = compile_to_dbt(
        _SPEC_SQL,
        project_dir,
        warehouse=get_settings().platform.warehouse_path,
        repo_root=_REPO,
    )
    log.info("regenerated {n} dbt models from spec/ into {p}", n=len(models), p=project_dir)
    return models


def _run(project_dir: Path, verb: str, *flags: str) -> None:
    argv = dbt_command(project_dir, verb, *flags)
    log.bind(task=f"dbt.{verb}").info("exec: {c}", c=" ".join(argv))
    subprocess.run(argv, check=True, cwd=_REPO)


@odos_task("dbt.deps")
def dbt_deps(*, project_dir: Path) -> None:
    """Install hub packages. Idempotent — dbt caches into `<project>/dbt_packages/`."""
    _regenerate(project_dir)
    if not (project_dir / "dbt_packages").is_dir():
        _run(project_dir, "deps")


@odos_task("dbt.parse")
def dbt_parse(*, project_dir: Path) -> None:
    """Refresh the manifest without running any model."""
    dbt_deps(project_dir=project_dir)
    _run(project_dir, "parse")


@odos_task("dbt.build")
def dbt_build(
    *,
    project_dir: Path,
    full_refresh: bool = False,
    select: str | None = None,
    state: str | None = None,
) -> None:
    """Run models + tests. The flag matrix that used to be six separate bash tasks."""
    dbt_deps(project_dir=project_dir)
    flags: list[str] = []
    if full_refresh:
        flags.append("--full-refresh")
    if select is not None:
        flags += ["--select", select]
    if state is not None:
        flags += ["--state", state]
    _run(project_dir, "build", *flags)
```

Добавьте в `src/ogip/tasks/__init__.py`, после существующего блока импортов:

```python
# Importing the task modules is what populates the registry. Keep this at the bottom: the
# modules import `odos_task` from `ogip.tasks._registry`, not from this package.
from ogip.tasks import dbt as dbt  # noqa: E402
```

- [ ] **Шаг 4: Запустите тест, чтобы убедиться, что он проходит**

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run pytest src/tests/unit/test_tasks_dbt.py -v`
Ожидается: PASS, 3 теста

- [ ] **Шаг 5: Проверьте регистрацию и гейты**

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run python -c "from ogip.tasks import task_names; print(task_names())"`
Ожидается: `['dbt.build', 'dbt.deps', 'dbt.parse']`

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run ruff check src/ogip/tasks && UV_PROJECT_ENVIRONMENT=.run/venv uv run pyright src/ogip/tasks`
Ожидается: ruff чист; pyright `0 errors`

- [ ] **Шаг 6: Коммит**

```bash
git add src/ogip/tasks/dbt.py src/ogip/tasks/__init__.py src/tests/unit/test_tasks_dbt.py
git commit -m "feat(tasks): dbt.build/parse/deps — one code path for both orchestrators

Six bash tasks collapse into dbt.build(full_refresh=, select=, state=).
Regeneration from spec/ is implicit; ensuring raw is deliberately not this
task's job.

Refs: #37"
```

---

### Задача 3: Задачи ingest, cdc, snapshot, integrations

**Файлы:**
- Создать: `src/ogip/tasks/ingest.py`, `src/ogip/tasks/cdc.py`, `src/ogip/tasks/snapshots.py`, `src/ogip/tasks/integrations.py`
- Изменить: `src/ogip/tasks/__init__.py` (расширить строку импорта регистрации)
- Тест: `src/tests/unit/test_tasks_registry.py` (дописать)

**Интерфейсы:**
- Потребляет: `odos_task`; `RawgGames` из `ingestion.sources.rawg`; `get_settings` из `ogip.config`.
- Производит: `ingest_rawg() -> str` (возвращает путь сырого вывода) · `parse_to_landing() -> None` ·
  `cdc_catchup(*, dry_run: bool = False) -> None` ·
  `snapshot_write(*, partition: str) -> int` (возвращает число строк) ·
  `trigger_prefect() -> None`.

Имена в реестре: `ingest.rawg`, `ingest.parse_to_landing`, `cdc.catchup`, `snapshot.write`,
`integrations.trigger_prefect`.

- [ ] **Шаг 1: Напишите падающий тест**

Допишите в `src/tests/unit/test_tasks_registry.py`:

```python
def test_the_whole_project_vocabulary_is_registered():
    """The closed vocabulary an ODOS spec may address. Adding a name is a deliberate act."""
    assert set(task_names()) >= {
        "cdc.catchup",
        "dbt.build",
        "dbt.deps",
        "dbt.parse",
        "ingest.parse_to_landing",
        "ingest.rawg",
        "integrations.trigger_prefect",
        "snapshot.write",
    }


def test_every_registered_task_is_keyword_only_or_zero_arg():
    """ODOS passes `args:` as a mapping, so tasks must not rely on positional parameters."""
    import inspect

    for name, fn in TASKS.items():
        params = inspect.signature(fn).parameters.values()
        positional = [
            p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        assert not positional, f"{name} takes positional parameters: {positional}"
```

- [ ] **Шаг 2: Запустите тест, чтобы убедиться, что он падает**

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run pytest src/tests/unit/test_tasks_registry.py -v`
Ожидается: FAIL на `test_the_whole_project_vocabulary_is_registered` — присутствуют только три имени `dbt.*`.

- [ ] **Шаг 3: Напишите минимальную реализацию**

Создайте `src/ogip/tasks/ingest.py`:

```python
"""Ingestion tasks — getting source data into the platform."""

from __future__ import annotations

from ogip.config import get_settings
from ogip.logger import log
from ogip.tasks._registry import odos_task

__all__ = ["ingest_rawg", "parse_to_landing"]


@odos_task("ingest.rawg")
def ingest_rawg() -> str:
    """Extract RAWG games via dlt → raw Parquet (Layer 0). Returns the output path.

    Unconditional. The Dagster lane used to skip this when parquet was already present; that
    condition now belongs to whoever composes the job, not to the task.
    """
    from ingestion.sources.rawg import RawgGames

    settings = get_settings()
    out = RawgGames(settings).run(settings.platform.data_dir)
    log.bind(source="rawg").info("raw landed at {p}", p=out)
    return str(out)


@odos_task("ingest.parse_to_landing")
def parse_to_landing() -> None:
    """Scraper/parser → Postgres `landing`. Placeholder until ADR-0014's ScraperSource lands."""
    log.warning(
        "ingest.parse_to_landing is a placeholder — wire the async ScraperSource (ADR-0014) here"
    )
```

Создайте `src/ogip/tasks/cdc.py`:

```python
"""CDC task — ingestr from the Postgres landing zone (D11)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ogip.logger import log
from ogip.tasks._registry import odos_task

__all__ = ["cdc_catchup"]

_REPO = Path(__file__).resolve().parents[3]
_CDC_SCRIPT = _REPO / "experimental" / "orchestration" / "dagster_ogip" / "cdc" / "ingestr_cdc.sh"


@odos_task("cdc.catchup")
def cdc_catchup(*, dry_run: bool = False) -> None:
    """Capture INSERT/UPDATE/DELETE on the Postgres `landing` schema and merge into the lake."""
    if not _CDC_SCRIPT.is_file():
        raise FileNotFoundError(f"CDC script not found at {_CDC_SCRIPT}")
    argv = ["bash", str(_CDC_SCRIPT)] + (["--dry-run"] if dry_run else [])
    log.bind(task="cdc.catchup").info("exec: {c}", c=" ".join(argv))
    subprocess.run(argv, check=True, cwd=_REPO)
```

Создайте `src/ogip/tasks/snapshots.py`:

```python
"""Snapshot task — the daily market snapshot fact, one Parquet per partition date."""

from __future__ import annotations

from ogip.config import get_settings
from ogip.logger import log
from ogip.tasks._registry import odos_task

__all__ = ["snapshot_write"]


@odos_task("snapshot.write")
def snapshot_write(*, partition: str) -> int:
    """Write one daily partition of the market snapshot; return the row count."""
    import duckdb

    settings = get_settings()
    warehouse = settings.platform.warehouse_path
    out = settings.platform.data_dir / "snapshots" / f"date={partition}"
    out.mkdir(parents=True, exist_ok=True)
    if not warehouse.exists():
        log.warning("warehouse absent at {p} — snapshot skipped", p=warehouse)
        return 0
    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        con.execute(
            f"copy (select date '{partition}' as snapshot_date, game_sk, title, "
            f"popularity_score, critic_score from fs.market_features) "
            f"to '{out / 'snapshot.parquet'}' (format parquet)"
        )
        result = con.execute("select count(*) from fs.market_features").fetchone()
    finally:
        con.close()
    rows = int(result[0]) if result else 0
    log.info("snapshot {d}: {n} rows", d=partition, n=rows)
    return rows
```

Создайте `src/ogip/tasks/integrations.py`:

```python
"""Cross-orchestrator integration tasks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ogip.logger import log
from ogip.tasks._registry import odos_task

__all__ = ["trigger_prefect"]

_REPO = Path(__file__).resolve().parents[3]


@odos_task("integrations.trigger_prefect")
def trigger_prefect() -> None:
    """Trigger the root Prefect flow — the two orchestrators over one spec and one warehouse."""
    log.bind(task="integrations.trigger_prefect").info("running pipelines.flows.main")
    subprocess.run([sys.executable, "-m", "pipelines.flows.main"], check=True, cwd=_REPO)
```

Замените строку регистрации внизу `src/ogip/tasks/__init__.py` на:

```python
# Importing the task modules is what populates the registry. Keep this at the bottom: the
# modules import `odos_task` from `ogip.tasks._registry`, not from this package.
from ogip.tasks import cdc as cdc  # noqa: E402
from ogip.tasks import dbt as dbt  # noqa: E402
from ogip.tasks import ingest as ingest  # noqa: E402
from ogip.tasks import integrations as integrations  # noqa: E402
from ogip.tasks import snapshots as snapshots  # noqa: E402
```

- [ ] **Шаг 4: Запустите тест, чтобы убедиться, что он проходит**

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run pytest src/tests/unit/test_tasks_registry.py -v`
Ожидается: PASS, 6 тестов

- [ ] **Шаг 5: Проверьте гейты**

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run ruff check src/ogip/tasks && UV_PROJECT_ENVIRONMENT=.run/venv uv run pyright src/ogip/tasks`
Ожидается: ruff чист; pyright `0 errors`

- [ ] **Шаг 6: Коммит**

```bash
git add src/ogip/tasks/ src/tests/unit/test_tasks_registry.py
git commit -m "feat(tasks): ingest, cdc, snapshot and integration tasks

Completes the closed vocabulary an ODOS spec may address. ingest.rawg is
unconditional — the Dagster lane's skip-if-parquet-present condition belongs to
job composition, not to the task body.

Refs: #37"
```

---

### Задача 4: Граница CLI

**Файлы:**
- Создать: `src/ogip/tasks/__main__.py`
- Тест: `src/tests/unit/test_tasks_registry.py` (дописать)

**Интерфейсы:**
- Потребляет: `get_task`, `task_names` из Задачи 1; все задачи из Задач 2–3.
- Производит: `parse_args(argv: list[str]) -> tuple[str, dict[str, object]]` · `main(argv: list[str] | None = None) -> int`.
  Форма CLI: `python -m ogip.tasks <name> [--key=value ...]`. Значения `true`/`false` становятся булевыми,
  цельночисловые значения становятся int, всё остальное остаётся строкой.

- [ ] **Шаг 1: Напишите падающий тест**

Допишите в `src/tests/unit/test_tasks_registry.py`:

```python
def test_cli_parses_name_and_typed_kwargs():
    from ogip.tasks.__main__ import parse_args

    name, kwargs = parse_args(["dbt.build", "--full_refresh=true", "--select=tag:daily"])
    assert name == "dbt.build"
    assert kwargs == {"full_refresh": True, "select": "tag:daily"}


def test_cli_coerces_ints_and_false():
    from ogip.tasks.__main__ import parse_args

    _, kwargs = parse_args(["probe.echo", "--retries=3", "--dry_run=false"])
    assert kwargs == {"retries": 3, "dry_run": False}


def test_cli_rejects_an_unknown_task_name_with_a_nonzero_exit():
    from ogip.tasks.__main__ import main

    assert main(["definitely.not.a.task"]) == 2


def test_cli_rejects_a_bare_flag_without_a_value():
    from ogip.tasks.__main__ import parse_args

    with pytest.raises(SystemExit):
        parse_args(["dbt.build", "--full_refresh"])
```

- [ ] **Шаг 2: Запустите тест, чтобы убедиться, что он падает**

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run pytest src/tests/unit/test_tasks_registry.py -v -k cli`
Ожидается: FAIL — `ModuleNotFoundError: No module named 'ogip.tasks.__main__'`

- [ ] **Шаг 3: Напишите минимальную реализацию**

Создайте `src/ogip/tasks/__main__.py`:

```python
"""`python -m ogip.tasks <name> [--key=value ...]` — the shell boundary of the registry.

Bash callers (`jobs/dg-tasks.sh`) and any orchestrator that prefers a subprocess reach the
tasks through here, so there is exactly one place where a task name becomes a call.
"""

from __future__ import annotations

import sys

from ogip.logger import log, setup_logging
from ogip.tasks._registry import TaskNotFoundError, get_task, task_names

__all__ = ["main", "parse_args"]


def _coerce(raw: str) -> object:
    if raw in ("true", "false"):
        return raw == "true"
    if raw.isdigit():
        return int(raw)
    return raw


def parse_args(argv: list[str]) -> tuple[str, dict[str, object]]:
    """Split ``<name> --k=v ...`` into the task name and its keyword arguments."""
    if not argv:
        raise SystemExit(f"usage: python -m ogip.tasks <name> [--key=value ...]\nknown: {', '.join(task_names())}")
    name, *rest = argv
    kwargs: dict[str, object] = {}
    for item in rest:
        if not item.startswith("--") or "=" not in item:
            raise SystemExit(f"expected --key=value, got {item!r}")
        key, _, value = item[2:].partition("=")
        kwargs[key] = _coerce(value)
    return name, kwargs


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    name, kwargs = parse_args(list(sys.argv[1:] if argv is None else argv))
    try:
        task = get_task(name)
    except TaskNotFoundError as exc:
        log.error("{e}", e=exc)
        return 2
    log.bind(task=name).info("running with {k}", k=kwargs)
    task(**kwargs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Шаг 4: Запустите тест, чтобы убедиться, что он проходит**

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run pytest src/tests/unit/test_tasks_registry.py -v`
Ожидается: PASS, 10 тестов

- [ ] **Шаг 5: Проверьте гейты**

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run ruff check src/ogip/tasks && UV_PROJECT_ENVIRONMENT=.run/venv uv run pyright src/ogip/tasks`
Ожидается: ruff чист; pyright `0 errors`

- [ ] **Шаг 6: Коммит**

```bash
git add src/ogip/tasks/__main__.py src/tests/unit/test_tasks_registry.py
git commit -m "feat(tasks): python -m ogip.tasks CLI boundary

Refs: #37"
```

---

### Задача 5: Провести линию Dagster через реестр

**Файлы:**
- Изменить: `experimental/orchestration/dagster_ogip/jobs/dg-tasks.sh` (заменить тела `case`)
- Тест: ручная проверка через `dg check defs` (у проекта Dagster собственный venv, и он не
  покрыт pytest-прогоном репозитория)

**Интерфейсы:**
- Потребляет: `python -m ogip.tasks <name> --k=v` из Задачи 4.
- Производит: ничего нового. `dg-tasks.sh <task>` сохраняет свои существующие имена задач, так что
  `defs/orchestration/*/definitions.py` не требует правки в этой задаче.

- [ ] **Шаг 1: Замените тело скрипта**

Перепишите `experimental/orchestration/dagster_ogip/jobs/dg-tasks.sh` ниже строки `set -euo pipefail`,
сохранив блок комментария-заголовка:

```bash
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$PROJECT" && git rev-parse --show-toplevel)"
cd "$REPO"

task="${1:?usage: dg-tasks.sh <build-dwh|build-dwh-full|dbt-evaluate|dbt-deps|update-dbt|update-dbt-changed|parsing|prefect|cdc>}"

# Every task is a thin alias for a registry call. The bodies live in `src/ogip/tasks/` so the
# Prefect lane runs the SAME code — see docs/superpowers/specs/2026-07-20-odos-*.md §2 for the
# drift this replaces.
ogip_task() { UV_PROJECT_ENVIRONMENT=.run/venv uv run python -m ogip.tasks "$@"; }

DBT_PROJECT="experimental/orchestration/dagster_ogip/dbt"

case "$task" in
  build-dwh)          ogip_task dbt.build --project_dir="$DBT_PROJECT" ;;
  build-dwh-full)     ogip_task dbt.build --project_dir="$DBT_PROJECT" --full_refresh=true ;;
  dbt-evaluate)       ogip_task dbt.build --project_dir="$DBT_PROJECT" --select=package:dbt_project_evaluator ;;
  update-dbt-changed) ogip_task dbt.build --project_dir="$DBT_PROJECT" --select=state:modified+ --state="$DBT_PROJECT" ;;
  dbt-deps)           ogip_task dbt.deps  --project_dir="$DBT_PROJECT" --force=true ;;
  update-dbt)         ogip_task dbt.parse --project_dir="$DBT_PROJECT" ;;
  parsing)            ogip_task ingest.parse_to_landing ;;
  prefect)            ogip_task integrations.trigger_prefect ;;
  cdc)                ogip_task cdc.catchup $([[ "${2:-}" == "--dry-run" ]] && echo "--dry_run=true") ;;
  *)
    echo "[dg-tasks] unknown task: $task" >&2
    exit 2
    ;;
esac
```

> **Изменение поведения, которое следует ожидать и принять:** `build-dwh` больше не ингестит сырые данные, когда
> parquet отсутствует (см. «Два решения» выше). Asset-job'ы Dagster уже выражают
> `raw → dbt` через выборку `dwh_assets_job`, так что это несёт граф, а не задача.
> Танец копирования манифеста `state:modified+` отбрасывается вместе с этим — `dbt.build` пробрасывает `--state`
> напрямую, а собственная ошибка dbt «нет предыдущего манифеста» — более понятный сбой, чем
> тихий полный build.

- [ ] **Шаг 2: Проверьте, что скрипт диспетчеризует**

Запустите: `bash experimental/orchestration/dagster_ogip/jobs/dg-tasks.sh update-dbt`
Ожидается: строки лога `regenerated N dbt models from spec/ into ...`, затем `exec: uv run --group
engines dbt parse --project-dir ...`, exit 0.

- [ ] **Шаг 3: Проверьте, что Dagster всё ещё загружается**

Запустите: `cd experimental/orchestration/dagster_ogip && uv run dg check defs`
Ожидается: `All components validated successfully` (или существующее сообщение об успехе проекта),
exit 0.

- [ ] **Шаг 4: Коммит**

```bash
git add experimental/orchestration/dagster_ogip/jobs/dg-tasks.sh
git commit -m "refactor(dagster): dg-tasks.sh dispatches to the ODOS registry

Nine bash bodies become nine one-line aliases. build-dwh no longer secretly
ingests raw — the asset graph already expresses that edge.

Refs: #37"
```

---

### Задача 6: Провести линию Prefect через реестр и доказать, что они согласованы

**Файлы:**
- Изменить: `pipelines/flows/_common.py:39-46` (`ingest_raw`) и `:48-66` (`build_warehouse`)
- Тест: `src/tests/unit/test_tasks_registry.py` (дописать тест эквивалентности)

**Интерфейсы:**
- Потребляет: `ingest_rawg`, `dbt_build` из Задач 2–3.
- Производит: без изменений сигнатур — `ingest_raw() -> str` и `build_warehouse(engine: str) ->
  list[str]` сохраняют свои имена и типы, так что `make_engine_flow` и каждый модуль `engines/prefect_*.py`
  остаются нетронутыми.

- [ ] **Шаг 1: Напишите падающий тест эквивалентности**

Допишите в `src/tests/unit/test_tasks_registry.py`:

```python
def test_both_lanes_reach_ingestion_through_the_same_registry_task():
    """The §2 drift guard.

    `dg-tasks.sh` and `pipelines/flows/_common.py` once had independent ingestion bodies — one
    conditional and routed through Dagster, one unconditional and straight to dlt. Both must now
    resolve to the single registry callable, so a change to one cannot miss the other.
    """
    from ogip.tasks import get_task
    from pipelines.flows import _common

    assert _common.ingest_raw is get_task("ingest.rawg")


def test_every_dg_tasks_branch_dispatches_to_the_registry():
    """Bash may alias registry calls; it may not carry logic of its own.

    Asserts on the shape of each `case` branch rather than on the absence of a substring: a
    branch that grows a second command, or invokes a tool directly, fails here.
    """
    import re
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    script = (
        repo / "experimental" / "orchestration" / "dagster_ogip" / "jobs" / "dg-tasks.sh"
    ).read_text(encoding="utf-8")
    body = script.split('case "$task" in', 1)[1].split("esac", 1)[0]

    branches = re.findall(r"^\s*([a-z0-9-]+)\)\s*(.+?)\s*;;\s*$", body, re.MULTILINE)
    assert len(branches) >= 8, f"expected the full task list, parsed {len(branches)} branches"
    for name, command in branches:
        assert command.startswith("ogip_task "), (
            f"branch {name!r} does not dispatch to the registry: {command!r}"
        )

```

- [ ] **Шаг 2: Запустите тест, чтобы убедиться, что он падает**

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run pytest src/tests/unit/test_tasks_registry.py -v -k both_lanes`
Ожидается: FAIL — `assert <function ingest_raw> is <function ingest_rawg>`

- [ ] **Шаг 3: Перепишите две функции**

В `pipelines/flows/_common.py` замените определение `ingest_raw` на ре-экспорт и измените
dbt-ветку `build_warehouse` на вызов реестра. Импорты вверху дополняются:

```python
from ogip.tasks.dbt import dbt_build
from ogip.tasks.ingest import ingest_rawg
```

Замените тело `ingest_raw` целиком:

```python
# Layer 0 ingestion is a registry task — the same callable the Dagster lane runs. Re-exported
# under the historical name so `make_engine_flow` and the engine modules stay untouched.
ingest_raw = ingest_rawg
```

Затем удалите импорт `RawgGames` и его строку `from ingestion.sources.rawg import RawgGames`
(теперь неиспользуемую), и в `build_warehouse` замените делегирование `transform.engines` **только для
движка `dbt`**:

```python
def build_warehouse(engine: str) -> list[str]:
    """Build ``staging → core → fs`` with ``engine``; return the model names."""
    get_settings().platform.warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    if engine == "sqlmesh":
        models = compile_to_sqlmesh(SPEC_SQL, SQLMESH_DIR / "models")
        log.info("compiled {n} SQLMesh models: {m}", n=len(models), m=models)
        subprocess.run(
            ["sqlmesh", "-p", str(SQLMESH_DIR), "plan", "--auto-apply", "--no-prompts"],
            check=True,
            cwd=REPO,
        )
        return models
    if engine == "dbt":
        # The registry task — byte-identical to what the Dagster lane runs.
        dbt_build(project_dir=REPO / "transform" / "dbt")
        return load_model_names()
    from transform.engines import run_transform_engine

    return run_transform_engine(engine)
```

Добавьте вспомогательную функцию рядом:

```python
def load_model_names() -> list[str]:
    """Model names from `spec/sql`, for the flow's return value."""
    from ogip.spec_compile import load_assets

    return [asset.name for asset in load_assets(SPEC_SQL)]
```

- [ ] **Шаг 4: Запустите тесты**

Запустите: `UV_PROJECT_ENVIRONMENT=.run/venv uv run pytest src/tests/unit/test_tasks_registry.py -v`
Ожидается: PASS, 12 тестов

- [ ] **Шаг 5: Запустите полный гейт**

Запустите: `make check`
Ожидается: ruff чист, pyright `0 errors`, pytest зелёный. Если `test_python_tasks.py` или
`test_pipeline_alerting.py` ломаются, они импортируют `_common.ingest_raw` для патчинга —
обновите цель патча на `ogip.tasks.ingest.ingest_rawg`, а не откатывайте ре-экспорт.

- [ ] **Шаг 6: Коммит**

```bash
git add pipelines/flows/_common.py src/tests/unit/test_tasks_registry.py
git commit -m "refactor(pipelines): Prefect lane runs the ODOS registry tasks

Closes the drift the registry exists to prevent: both orchestrators now reach
ingestion through ingest.rawg and dbt through dbt.build. Two tests pin it — one
asserts the identity of the callable, one forbids dg-tasks.sh from building dbt
commands of its own.

Refs: #37"
```

---

## Follow-up'ы, которые этот план намеренно откладывает

- **Консолидировать две директории dbt-проектов** (`transform/dbt` против сгенерированного `dbt/`
  проекта Dagster). Требует перенаведения `DbtProjectComponent` и пересмотра ADR-0015.
- **`transform/engines.py:_run_dbt`** всё ещё строит собственный dbt argv для профилей сравнения.
  Он должен вызывать `dbt_build`, как только уладится вопрос о project-dir выше.
- **Планы 2 и 3** — ODOS IR + фронтенд + `to_dagster.py`, затем `to_prefect.py` + полный
  harness эквивалентности. Оба зависят от существования этого реестра.
