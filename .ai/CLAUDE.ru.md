<!-- ru-translation-of: .ai/CLAUDE.md sha:7153156bc605 -->
<!-- Автоперевод. Источник — .ai/CLAUDE.md. Правьте источник, затем /translate-md-docs-to-russian. -->

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

- Пофазная поставка с **гейтами одобрения пользователя** после каждой фазы
  (план: [PLAN.md](PLAN.md) · статус: [STATUS.md](STATUS.md) · задачи: [tasks/](tasks/)).
- После каждой фазы: объясните решения, покажите дерево, спросите одобрение перед продолжением.
- Пакетная/разовая работа идёт через скрипты в `.tmp/` (`.tmp/.once/` для одноразовых);
  долговечные интерфейсы — в Makefile/Justfile + документацию.
- Коммиты по конвенциям /smart-commit: Conventional Commits, разбиение по категориям
  (chore(ai)/docs/ci/feat/test).
- **Push без спроса** — постоянная авторизация, без пер-push-гейта. Предусловия, все
  сразу, каждый раз:
  1. `make check` (или CI-эквивалентное подмножество) **зелёный локально** для файлов, которыми вы владеете.
  2. Вы пушите **только коммиты своей lane** — параллельные сессии делят эту ветку, поэтому
     `git log origin/<branch>..HEAD` не должен содержать ничего, что писали не вы. Никогда не пушьте
     работу другой lane, тем более красную, чтобы протолкнуть свою.
  3. Каждый коммит несёт `Refs: #<issue>` / `Closes: #<issue>` (принуждается
     `.ci/steps/commit-binding.sh`).
  4. **Никогда не делайте force-push** в общую ветку (`main`, `dev`) — сюда коммитят 4+ агентских сессий, и
     переписывание истории уничтожает их незавершённую работу. Без исключений.
- Ветки: работа приземляется в **`dev`**; `dev → main` идёт через **PR** с зелёным CI
  (`.github/workflows/ci.yml` уже запускается на `pull_request`). `main` остаётся релизуемой.

## Скиллы

Прежде чем тянуться за каталожным скиллом, прочитайте **[SKILLS.md](SKILLS.md)**. Общий каталог построен
в основном для GitLab + Jira + ClickHouse; ~193 из его 521 скилла нацелены на инфраструктуру, которой у OGIP
нет, и они отказывают *беззвучно* — корректно оформленная Jira-задача для проекта без Jira. `SKILLS.md`
перечисляет, что здесь используется (с файловыми свидетельствами), что подходит стеку и что не трогать.

## Команды (целевые — создаются в Phase 0)

- Гейты: `make check` (= ruff + pyright strict + pytest); паритет с CI: `make ci`
- Запуск: `make run` (полный пайплайн на сэмпл-данных); `just run-profile <name>` (профили A12)
- Инфраструктура: `make up` / `make obs-up` / `make down` (compose: `deploy/docker-compose.yml`, env: отрендеренный `.env`)
- Конфиг: правьте `config/config.yml` → `make render-env` (никогда не правьте производные значения `.env`)
- Runtime-окружение: `UV_PROJECT_ENVIRONMENT=.run/venv` (экспортируется всеми build-файлами)

## Ключевые пути

`src/ogip/` (пакет) · `ingestion/` (base/common/sources) · `spec/` (SSoT: контракты + Bruin SQL) ·
`transform/` (SQL-раннер) · `dq/` · `pipelines/` (Prefect) · `outputs/`+`examples/` ·
`experimental/` (engines/orchestration/semantic/bi — вне production-пути) · `deploy/` · `config/` ·
`docs/` · `.run/` (runtime, gitignored).
