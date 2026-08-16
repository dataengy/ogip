<!-- ru-translation-of: .ai/SKILLS.md sha:96bd9e276a44 -->
<!-- Автоперевод. Источник — .ai/SKILLS.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [SKILLS.md](SKILLS.md)

# `.ai/SKILLS.md` — какие агентские скиллы применимы к OGIP

Общий каталог (`~/.ai/skills/_catalog/`, **521 скилл**) построен в основном для *корпоративной
платформы GitLab + Jira + ClickHouse*. OGIP — **публичный OSS на GitHub с DuckDB**. Примерно
**193 из этих 521 скилла нацелены на инфраструктуру, которой у этого проекта нет** — так что «в каталоге
есть скилл для этого» не является свидетельством того, что скилл применим здесь.

Этот файл — фильтр. Он существует потому, что агент, тянущийся за `/merge-mr` или `/add-jira-task` в
этом репозитории, не падает громко — он производит уверенную, правдоподобную, неверную работу.

**Правило свидетельств:** скилл попадает в раздел *«В использовании»* только с файлом, который на него ссылается. Всё
остальное — рекомендация, и помечено как таковая.

---

## 1. В использовании — на них ссылается этот репозиторий

| Скилл | Где OGIP на него ссылается | Что он здесь делает |
|---|---|---|
| `/agent-session-lock` | [`STATUS.md`](STATUS.md), [`tasks/session-coordination.md`](tasks/session-coordination.md), [`src/scripts/lane.sh`](../src/scripts/lane.sh) | **Обязателен перед любой записью.** 4+ сессий одновременно коммитят в `dev`; `lane.sh` оборачивает этот примитив. |
| `/add-data-source` | [`.claude/agents/ogip-ingestion-engineer.md`](../.claude/agents/ogip-ingestion-engineer.md) | Хребет инжеста: probe → tier → legality → коннектор + контракт + staging + тест → ship. |
| `/find-sources-and-match-tool` | тот же файл агента, `.claude/settings.local.json` | Его исследовательская половина — заявки реестра, живой probe, детерминированная маршрутизация инструментов. |
| `/add-terms-to-glossary`, `/update-terms-glossaries` | [`AI-glossary.en.md`](AI-glossary.en.md), [`AI-glossary.ru.md`](AI-glossary.ru.md) | **Единственный** санкционированный способ править глоссарии. Никогда не правьте их вручную. |
| `/smart-commit` | [`CLAUDE.md`](CLAUDE.md) | Конвенции коммитов, когда `ship.sh` не подходит. |
| `/add-secret` | [`src/scripts/ask-secret-gui.sh`](../src/scripts/ask-secret-gui.sh) | Приём секрет-слотов. Никогда не выдумывайте креденшел; пустой слот — это вопрос пользователю. |
| `/check-secrets` | [`tasks/vps-deploy-tooling.md`](tasks/vps-deploy-tooling.md) | Полнота секретов перед деплоем. |
| `/github-auth-ensure` | хук SessionStart в [`.claude/settings.json`](../.claude/settings.json) | Аутентифицируется ли `git push` под аккаунтом, который **владеет** `dataengy/ogip`? Один push здесь упал с `denied to hnkovr`, хотя правильный токен уже лежал на диске — его затенял URL-скоупнутый credential helper. Хук предупреждает только при несовпадении. |
| `/verify-project-local-full` | [`config/verify.yml`](../config/verify.yml) `local:`, [`.claude/agents/ogip-cloud-devops.md`](../.claude/agents/ogip-cloud-devops.md) | Полная локальная верификация проекта: гоняет матрицу (стадии CI-паритета + obs/compose) с реальными кодами выхода. |
| `/verify-project-cloud-deployable` | [`config/verify.yml`](../config/verify.yml) `cloud:`, тот же агент | Деплоябельность вне рабочей станции: ассеты, ранбуки, CI, эскроу секретов, прогон `vps-*-dry`. `NEEDS-OPERATOR` на слотах, заполняемых человеком, — ожидаемая форма. |
| `/propose-project-deploy` | [`tasks/cloud-devops-readiness.md`](tasks/cloud-devops-readiness.md) | Предложение деплоя за человеческим гейтом (только slash). Никогда не деплоит; ADR-0012 оставляет деплои ручными. |

## 2. Применимы к стеку — рекомендованы, но ещё не подключены

Сопоставлены с реальными движками OGIP (Prefect · dbt/SQLMesh/Bruin · DuckDB · Dagster · GitHub
Actions). Это те, за которыми стоит тянуться; ни один пока не упомянут в репозитории.

| Скилл | Когда использовать |
|---|---|
| **`/generate-odcs-specs`** | Авторинг или обновление любого `spec/contracts/<system>/<system>__<entity>.odcs.yaml`. **Это авторитет по ODCS** — шаг 4, пункт 2 `/add-data-source` должен вызывать его, а не переизлагать авторинг контрактов. |
| **`/generate-agnostic-bruin-sql-specs`** | Написание чего угодно в `spec/sql/` — стюард портабельного SQL-формата `@bruin`→`@odts`. |
| **`/spec-compile-engines`** | Компилятор «один spec → N движков» (dbt · SQLMesh · Bruin · plain SQL). Прямо соответствует архитектуре трансформаций OGIP. |
| **`/integrate-sql-tool-with-prefect`** | Добавление Prefect-flow на движок. Соответствует решению «один flow на SQL-движок», уже зафиксированному в памяти проекта. |
| **`/call-dagster-from-prefect`** | Шов «Dagster внутри Prefect» — `.github/workflows/dagster-e2e.yml` уже упражняет эту форму. |
| **`/add-dagster-module`**, `/add-dagster-odp-module`, `/integrate-dagster-with-dbt` | Работа внутри `experimental/orchestration/`. |
| **`/verify-gate-actually-covers`** | **Каждый раз, когда добавляется CI-гейт, prek-хук или регрессионный тест.** Гейт, не совпадающий ни с одним файлом, выглядит в точности как проходящий гейт — и этот репозиторий уже отгружал один прозаический «гейт», который ничто не принуждало. |
| **`/e2e-ship`** | Ship-on-green: прогнать e2e, затем commit + push + уведомление. |
| **`/handoff-prompts`** | Раздача остатков работы другим сессиям (используется [`docs/superpowers/plans/2026-07-20-handoff-prompts.md`](../docs/superpowers/plans/2026-07-20-handoff-prompts.md)). |
| **`/sync-with-parallel-session`** | Перед merge/рестартом, которым может владеть другая живая сессия. |
| **`/session-artifacts-to-tmp`** | Захват ad-hoc-скриптов этой сессии в `.tmp/` по конвенции пакетной работы проекта. |
| **`/upsert-doc-about-runbook`**, `/upsert-doc-about-roadmap`, `/validate-docs` | `docs/runbooks/`, `docs/ROADMAP.md`, гигиена документации. |
| **`/ensure-git-repo`**, `/update-gitignore`, `/remove-from-git-index` | Гигиена репозитория. |
| **`/use-log-alias`** | Конвенция `log`-не-`logger`, принуждаемая по всему проекту. |

## 3. НЕ тянитесь здесь за этими

Не «более низкий приоритет» — **не та инфраструктура**. Каждый произвёл бы работу против системы, которую OGIP
не использует.

| Семейство | Кол-во | Почему не применимо к OGIP |
|---|---|---|
| Трекеры Jira / Tempo / PNF / Todoist / Linear | **81** | OGIP ведёт работу в **GitHub Issues** (`just tasks-sync`, `Refs: #<n>` принуждается `.ci/steps/commit-binding.sh`). В этом репозитории нет ни одной ссылки на Jira. |
| GitLab `glab` / ревью MR / merge-процессы | **36** | OGIP — это **GitHub**; `dev → main` идёт через GitHub PR с `.github/workflows/ci.yml`. Никаких MR не существует. |
| `host-ops` — SSH-парк, cron-хосты, Zabbix, туннели | **50** | У OGIP нет управляемого парка хостов. Деплой — локальный compose + одна VPS-задача. |
| Операции ClickHouse + dbt-сабмодуля | **26** | Хранилище — **DuckDB**. dbt существует только как один *генерируемый* движок под `experimental/`, никогда как сабмодуль. |

**Ловушка, которую предотвращает эта таблица:** эти скиллы хорошо написаны и охотно выполнятся. Отказ
беззвучен — корректно оформленная Jira-задача для проекта без Jira, вызов `glab` против
репозитория без GitLab-remote. Сверяйтесь с этой таблицей до того, как потянуться, а не после.

## 4. Пробелы — предложены, ещё не созданы

Четыре способности имеют **нулевое** покрытие среди всех 521 скилла: описание бизнес-ценности источника,
проектирование пайплайна source→landing→staging, **генерация синтетических фикстур** (0 совпадений по всему каталогу) и
авторинг коннекторов под конкретный движок.

Полная декомпозиция, с аудитом переиспользования и трёхволновым порядком сборки:
[`docs/superpowers/plans/2026-07-20-add-data-source-skill-decomposition.md`](../docs/superpowers/plans/2026-07-20-add-data-source-skill-decomposition.md).

Ничего из этого ещё не создано. Создание гейтировано и идёт через `/propose-skill-for-that` →
`/create-skill` → `/save-all-deterministic-for-skill-as-scripts` — **файлы скиллов никогда не пишутся
вручную.**

## 5. Скилл, который должен поддерживать этот файл — обобщайте, а не создавайте

Этот файл собран вручную. Так быть не должно, и **исправление — это не новый скилл.**

`/analyse-pdp-skill-usage` уже делает счётную половину: он сканирует корень проекта на известные слаги
по планам, FIXME, TODO и сессиям и выдаёт `skill-usage.yml` + `skill-task-map.md` +
`used-skills.list`. Два изменения заставят его производить §1–§3 этого документа:

1. **Обобщить его за пределы PDP.** Его корень проекта уже вынесен в `settings/defaults.yml`;
   переименование `analyse-pdp-skill-usage` → `analyse-project-skill-usage` — ровно то, для чего существует
   `/refactor-repo-root-to-project-param`. Почти механически.
2. **Добавить фильтр применимости, которого ему не хватает.** Подсчёт использования отвечает на вопрос *«какие скиллы этот
   проект упоминает»*. Он не отвечает на вопрос *«какие скиллы молча произвели бы здесь неверную работу»* —
   §3 выше, самая ценная часть. Для этого нужна попроектная декларация возможностей (tracker =
   github|jira · vcs-host = github|gitlab · warehouse = duckdb|clickhouse · парк хостов = yes|no),
   сверяемая с областью каждого скилла.

Создание свежего скилла `index-project-skills` вместо этого оставило бы два пересекающихся сканера дрейфовать
врозь — ровно то дублирование, от которого защищает `/split-skill-on-subskills`.

## 6. Как держать этот файл честным

- Скилл переезжает из §2 в §1 только тогда, когда на него ссылается реальный файл. Не продвигайте по намерению.
- **Проверяйте перед тем, как рекомендовать.** Каталожные скиллы правятся вне этого репозитория; подтверждайте, что слаг всё ещё
  существует: `just -f ~/.ai/skills/_scripts/skills/management/Justfile skill-locate <slug>`.
- **Копии скиллов дрейфуют беззвучно.** `~/.claude/skills/<slug>/skill.md` может оказаться независимой устаревшей
  копией, а не хардлинком на каталог — `/add-data-source` был пойман на версии, отстающей на 3 дня
  и 6 KB, без единого симптома. После любой правки каталога запускайте `skill-sync-state <slug>` и чините
  `STALE`; реально чинит это `hardlink-skill-files <catalog-dir> <target-dir>`.
- Счётчики §3 — снимок (2026-07-20) растущего каталога. *Рассуждение* стабильно; числа — нет.
