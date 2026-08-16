<!-- ru-translation-of: .ai/tasks/phase-0-scaffold.md sha:b4104cc6c4c2 -->
<!-- Автоперевод. Источник — .ai/tasks/phase-0-scaffold.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [phase-0-scaffold.md](phase-0-scaffold.md)

# Задача — Фаза 0: каркас (scaffold) и идентичность проекта

**Статус:** ✅ готово — `make check` зелёный (ruff · pyright strict 0 ошибок · 6 тестов), `uv sync` OK.

## Сделано

- `git init` (main); `pyproject.toml` (`ogip`, py3.13, uv; зависимости dlt/sqlmesh/prefect/duckdb/
  pyarrow/psycopg; группы dev[+jupyterlab], ingestr, engines, dagster); конфигурация ruff/pyright/sqlfluff/pytest.
- Типизированное ядро `src/ogip/{__init__,config,logger}.py` + `py.typed` (портировано из OGAP, `ogap`→`ogip`).
- SSoT конфигурации `config/config.yml` + `.env-render.py` (merge-safe секреты) + `.pre-commit-config.yaml`
  (prek) + `.yamllint.yaml`.
- Сборочные файлы `Makefile` + `Justfile` (root-lean); `.gitignore`, `.python-version`, `LICENSE`, `README.md`.
- CI: `.ci/run.sh` + шаги (lint · typecheck · test · sql-lint · bash-lint · structure-validate ·
  secret-scan) + `.github/workflows/ci.yml`.
- Тесты: `src/tests/{smoke,unit}` (уровни smoke/unit/integration/e2e).
- Симлинки `.ai/` (memory·skills в gitignore; specs→../spec, scripts→../src/scripts отслеживаются);
  симлинки в корне `AGENTS.md` + `.claude/CLAUDE.md`.
- Заглушки каталогов + README: ingestion/ transform/ pipelines/ dq/ spec/ src/scripts/ config/ .ci/ src/tests/.

## Решения, зафиксированные в этой фазе

- **D15** commit + push после каждого успешного прогона (зелёный gate/пайплайн).
- **D16** pre-commit через **prek** (быстрый, drop-in) — линт ВСЕГО (Python·SQL·Bash·YAML) + smoke-тесты
  на commit, data-тесты на pre-push, скан секретов gitleaks.
- **D17** уровни тестов smoke / unit / integration / **e2e = запустить Prefect-джобу + проверить результаты**.
- **D18** root-lean: конфиги→`config/`, тесты→`src/tests/`, скрипты→`src/scripts/`, CI→`.ci/`;
  guard `structure-validate` следит за соблюдением.
- **D19** симлинки `.ai/` для планов/memory/skills (memory·skills в gitignore; specs·scripts отслеживаются).

## Отложено (сделать ПОЗЖЕ)

- **D20** Внести установленные здесь стандарты кода и каркаса проекта в
  `~/.ai/skills/.settings/code_specs/` (python_module_layout · script_standards · justfile_standards)
  — root-lean-структуру, набор pre-commit-хуков prek, уровни тестов, цикл commit+push, конвенцию симлинков `.ai/`.

## Далее → M0 (walking skeleton)

RAWG → raw Parquet → 1-й контракт ODCS + Bruin SQL → SQLMesh (stg→core→mart/fs) → 1 ML-parquet →
ноутбук + Evidence, на Prefect-флоу (dlt). Затем `make up` (Docker) + зелёная Prefect-джоба.
