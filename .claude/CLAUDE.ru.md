<!-- ru-translation-of: .claude/CLAUDE.md sha:7153156bc605 -->
<!-- Автоперевод. Источник — .claude/CLAUDE.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [CLAUDE.md](CLAUDE.md)

# OGIP — инструкции проекта (Claude Code)

**OGIP (Open Games Intelligence Platform)** — production-grade OSS **Market Intelligence
Platform** для игровой индустрии; продукт = **ML-ready Parquet-датасеты** для DS/ML/аналитиков.
Витрина портфолио-качества для навыков Senior/Staff Data Engineer. Преемник OGAP
(`../Hushcrasher/`), намеренно проще.

**Основные правила живут в [AGENTS.md](AGENTS.md)** (та же директория) — общие правила, принцип
«production-путь священен», закон именования слоёв, SSoT `spec/` (Bruin + ODCS),
SSoT-конфиг, планка качества, профили запуска. Этот файл добавляет только Claude-специфичные заметки о рабочем процессе.

## Рабочий процесс

- Поэтапная поставка с **гейтами одобрения пользователя** после каждой фазы
  (план: [PLAN.md](PLAN.md) · статус: [STATUS.md](STATUS.md) · задачи: [tasks/](tasks/)).
- После каждой фазы: объяснить решения, показать дерево, спросить одобрение перед продолжением.
- Пакетная/разовая работа идёт через скрипты в `.tmp/` (`.tmp/.once/` для one-shot'ов);
  долговечные интерфейсы уходят в Makefile/Justfile + доки.
- Коммиты по конвенциям /smart-commit: Conventional Commits, с разбивкой по категориям
  (chore(ai)/docs/ci/feat/test).
- **Push без спроса** — постоянная авторизация, без пер-push-гейта. Предусловия — все,
  каждый раз:
  1. `make check` (или CI-эквивалентное подмножество) **зелёный локально** для файлов, которыми вы владеете.
  2. Вы пушите **только коммиты своего lane** — параллельные сессии делят эту ветку, поэтому
     `git log origin/<branch>..HEAD` не должен содержать ничего, что написали не вы. Никогда не пушьте
     работу другого lane, особенно красную, чтобы приземлить свою.
  3. Каждый коммит несёт `Refs: #<issue>` / `Closes: #<issue>` (принуждается
     `.ci/steps/commit-binding.sh`).
  4. **Никогда не делайте force-push** общей ветки (`main`, `dev`) — сюда коммитят 4+ агентных сессий, и
     перезапись уничтожает их незавершённую работу. Без исключений.
- Ветки: работа приземляется на **`dev`**; `dev → main` идёт через **PR** с зелёным CI
  (`.github/workflows/ci.yml` уже запускается на `pull_request`). `main` остаётся релизопригодной.

## Навыки

Прежде чем тянуться к каталожному навыку, прочитайте **[SKILLS.md](SKILLS.md)**. Общий каталог построен
в основном для GitLab + Jira + ClickHouse; ~193 из его 521 навыка нацелены на инфраструктуру, которой у OGIP
нет, и они отказывают *тихо* — корректно оформленная Jira-задача для проекта без Jira. `SKILLS.md`
перечисляет, что используется здесь (с файловыми свидетельствами), что подходит стеку и что не трогать.

## Команды (целевые — создаются в Фазе 0)

- Гейты: `make check` (= ruff + pyright strict + pytest); паритет с CI: `make ci`
- Запуск: `make run` (полный пайплайн на сэмпл-данных); `just run-profile <name>` (профили A12)
- Инфра: `make up` / `make obs-up` / `make down` (compose: `deploy/docker-compose.yml`, env: отрендеренный `.env`)
- Конфиг: правьте `config/config.yml` → `make render-env` (никогда не правьте производные значения `.env`)
- Runtime-окружение: `UV_PROJECT_ENVIRONMENT=.run/venv` (экспортируется всеми файлами сборки)

## Ключевые пути

`src/ogip/` (пакет) · `ingestion/` (base/common/sources) · `spec/` (SSoT: контракты + Bruin SQL) ·
`transform/` (SQL-раннер) · `dq/` · `pipelines/` (Prefect) · `outputs/`+`examples/` ·
`experimental/` (engines/orchestration/semantic/bi — вне prod-пути) · `deploy/` · `config/` ·
`docs/` · `.run/` (runtime, gitignored).
