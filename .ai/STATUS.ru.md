<!-- ru-translation-of: .ai/STATUS.md sha:b61c674a7cb4 -->
<!-- Автоперевод. Источник — .ai/STATUS.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [STATUS.md](STATUS.md)

# OGIP — Статус

_Последнее обновление: 2026-07-30_

## Текущая фаза

**Финализационный прогон (2026-07-30, режим AUTO)** — действующий план (plan of record):
[docs/superpowers/plans/2026-07-30-finalization-land-everything.md](../docs/superpowers/plans/2026-07-30-finalization-land-everything.md),
зонтичная задача [tasks/finalization.md](tasks/finalization.md). Состояние: **re-root ГОТОВ** (#40, PR #46
смержен — dbt primary + bruin co-primary, ADR-0020); **три демо-команды зелёные** на sample-данных
(`make run-dbt` · `run-bruin` · `run-dagster-dbt`, последняя доказана на очищенном
warehouse); **DQ-мониторы исполняются по-настоящему** (row_count+freshness на DuckDB, error → exit 1,
подключены в `make check` + e2e-шаг CI); выведенные из работы ветки СОХРАНЕНЫ и помечены как устаревшие
([реестр stale-веток](../docs/techdebt/stale-branches.md) — директива владельца: помечать, никогда не
удалять); замороженные фичи отслеживаются в [реестре техдолга](../docs/techdebt/finalization-tbd.md). В
работе: догон dagster #34 (агент), odos #37, dev→main (#10).

**M0 — walking skeleton: ✅ ОТГРУЖЕН.** RAWG → сырой Parquet (**dlt**) → **SQLMesh** (raw→stg→core→fs,
компилируется из Bruin-спецификации) → ML-ready `games.parquet` + `market_features.parquet` → демо-ноутбук,
всё под управлением **Prefect**-flow (ephemeral, без Docker). `make check` зелёный; **e2e-тест запускает
Prefect-джобу в CI**; CI зелёный (7/7). Репозиторий: [github.com/dataengy/ogip](https://github.com/dataengy/ogip).
Детали: [tasks/m0-walking-skeleton.md](tasks/m0-walking-skeleton.md).

Фаза 0 (scaffold) тоже ✅ отгружена — [tasks/phase-0-scaffold.md](tasks/phase-0-scaffold.md).

**Репроприоритизировано 2026-07-17** (SWOT против брифа целевого use-case):
**P1 — устойчивый срез скрейпинга** ([tasks/scraping-resilient.md](tasks/scraping-resilient.md),
lane `ingestion`, [ADR-0014](../docs/adr/ADR-0014-resilient-scraping-concurrency.md)) ·
**P1 — финализация R2 + деплоя на VPS** ([tasks/r2-vps-finalize.md](tasks/r2-vps-finalize.md) —
все оставшиеся пункты находятся в lane `core-pipeline`) · **P2 — бэклог источников**
([tasks/sources-backlog.md](tasks/sources-backlog.md)). Тиражирование тулсетов M1–M4 понижено
ниже P1. Открытые вопросы по требованиям (скрейпинг · объёмы · serving/FS/семантика ·
SQL+Python): [docs/OPEN-QUESTIONS.md](../docs/OPEN-QUESTIONS.md).

## Lanes параллельных сессий (перед записью займите lock!)

Работа распределена по параллельным агентским сессиям. **Займите свой lane** объектным lock'ом
перед записью и сначала выполните settle-check (`git fetch` + `agent-lock check`):

```bash
bash ~/.ai/skills/_scripts/session/agent-session-lock.sh acquire --repo . --object <lane> --reason "..."
```

| Lane (объект lock'а) | Охват | Владелец |
|---|---|---|
| `core-pipeline` | `spec/` `src/ogip/` `transform/` `pipelines/` `config/` `.ci/` | параллельная сессия — альтернативные профили M1; **lock ПРОТУХ (STALE) с 16:00** (см. аудит lock'ов ниже); также владеет всеми пунктами `r2-vps-finalize` |
| `ingestion` | `ingestion/` (реестр источников, коннекторы, посадка raw) — **выделен из `core-pipeline` 2026-07-17** | параллельная сессия (живая) — дом **P1-среза скрейпинга** |
| `obs` | `deploy/obs/`, `src/scripts/obs-*.sh`, `docs/architecture/observability.md` | **параллельная сессия** — стек Фазы 7 отгружен; 2 handoff'а ниже |
| `evidence` | `experimental/bi/evidence/` | параллельная сессия |
| `dagster` | `experimental/orchestration/dagster*`, профиль `prefect-dagster-dlt-dbt` | параллельная сессия |
| `vps` | `deploy/vps/`, рецепты `vps-*`, `config/config.yml → deploy.vps.*` | **параллельная сессия** — тулинг отгружен; 1 handoff ниже |
| `s3` | MinIO в `deploy/`, конфиг `storage`, S3-назначение dlt/duckdb | параллельная сессия |
| `alerting` | `src/ogip/alerting/`, `src/tests/unit/test_alerting.py` | **параллельная сессия** — Notifier + tg/mm/slack отгружены ([#11](https://github.com/dataengy/ogip/issues/11)); 1 handoff ниже |

Используйте **скрипт напрямую**, а не `just -f … agent-lock` — его рецепт повторно парсит
`--reason` через `bash -c`, поэтому скобки его ломают.

**Аудит lock'ов 2026-07-30.** Все протухшие lock'и сломаны (obj--airbyte в основном дереве;
obj--core-pipeline и obj--dagster жили в **worktree-локальных** хранилищах — помните, у каждого
связанного worktree свой `.ai/.locks/`, невидимый из основного дерева). Жив только `repo`-lock
финализационной сессии; сейчас это **единственная** живая агентская сессия в этом репозитории.
Таблица lanes выше — историческая: lanes-заглушки (evidence/obs/s3/vps) и
ветки, оставшиеся только влитыми (merged-only), удаляются на шаге 18 финализации; `dagster` и `odos` приземляются через
PR #34 / #37.

### Handoffs: lane `obs` → lane `core-pipeline`

Стек Фазы 7 работает (`make obs-up`), но его обращённая к пайплайну половина находится в **вашем** lane —
`config/` и `pipelines/` заблокированы за вами, поэтому obs-сессия их не трогала:

1. **Flow не пишет лог-файл** → Alloy «хвостит» пустую директорию, панели логов остаются пустыми.
   `pipelines/flows/main.py:78` вызывает голый `setup_logging()`; `src/ogip/config.py` уже
   экспонирует обе нужные ему ручки —
   `setup_logging(json_logs=settings.log_json, log_file=settings.log_file)`.
   Для распарсенных лейблов Loki дополнительно нужен `platform.log_json: true` в `config/config.yml`.
2. **Порты obs не доходят до `.env`** → `config/config.yml` объявляет `victoriametrics_port`,
   `loki_port`, `grafana_port`, но `config/.env-render.py` → `_derived()` их не маппит, поэтому
   compose откатывается к литералам, дублирующим SSoT. Закрывается тремя строками.

Опционально позже: экспортировать OTLP-метрики на `localhost:4318` (префикс `ogip_`) — Alloy их
уже принимает, и панель дашборда ждёт. Детали:
[docs/architecture/observability.md](../docs/architecture/observability.md) → «Not wired yet».

### Handoff: lane `alerting` → lane `core-pipeline`

`src/ogip/alerting/` поставляет `Notifier` + Telegram/Mattermost/Slack ([#11](https://github.com/dataengy/ogip/issues/11),
[tasks/alerting.md](tasks/alerting.md)) — проверено против живого Telegram API. Только новые файлы;
ничего вашего не редактировалось. Одна вещь намеренно оставлена вне SSoT и требует вас:

- **Маршрутизация живёт в env-переменных, а не в `config/config.yml`** — потому что этот файл и
  `config/.env-render.py` — ваши. Чтобы закрыть: добавьте секцию `alerting:` (`backend`,
  `fallback_backend`, `dry_run`), замаппьте её в `_derived()`, добавьте слоты секретов
  (`OGIP_TG_BOT_TOKEN`, `OGIP_MM_TOKEN`, `OGIP_MM_WEBHOOK_URL`, `OGIP_SLACK_TOKEN`,
  `OGIP_SLACK_WEBHOOK_URL`), затем замените литеральные дефолты в `alerting/settings.py` на
  `_yaml("alerting", …)`. Имена env уже несут префикс `OGIP_`, так что коллизий пространств имён нет.

~~Также ваше, если хотите, чтобы алерты действительно срабатывали: в `pipelines/flows/` нет hook'а на сбой.~~
**Готово 2026-07-18** (lane был FREE, core-pipeline удерживался кратко): `pipelines/alerting_hooks.py`
→ `notify_flow_failure` подключён как `on_failure=[…]` на flow. Проверено запуском — Prefect
вызывает его при реальном сбое, и он собирает `🔴 OGIP flow failed: <flow> / run: <run> / state:
<exception>`. Молчит без кредов (`make_notifier()` — `None`), никогда не бросает исключений.
По-прежнему открыто по SSoT: пункт про маршрутизацию-в-env-переменных выше без изменений.

### Handoff: lane `hygiene` → lane `core-pipeline`

`src/scripts/public-hygiene.sh` отказывается публиковать идентификаторы чужой организации
(id трекеров, внутренние хосты, приватные пути checkout'ов, имена org/ботов) — та половина
утечки, которую gitleaks не покрывает, поскольку это не секреты, а просто «не наше». Он
существует потому, что агентский файл в этом репозитории слил приватный путь в публичный
коммит, несмотря на ручной grep. Новый файл, обкатан (5/5 маркерных паттернов покрыты
unit-проверкой, и он поймал реальную утечку, уже исправленную). Он ещё не является gate'ом —
чтобы его подключить (оба пункта в вашем lane):

1. **CI**: добавить `.ci/steps/public-hygiene.sh` (одна строка: `source _common.sh; exec bash
   "$REPO_ROOT/src/scripts/public-hygiene.sh"`) и дописать `public-hygiene` в список шагов в
   `.ci/run.sh` и в `.github/workflows/ci.yml`.
2. **prek**: добавить локальный hook в `config/.pre-commit-config.yaml`
   (`entry: bash src/scripts/public-hygiene.sh`, `language: system`, `pass_filenames: false`).

Список маркеров — литерал внутри скрипта, а не в `config/config.yml`, по той же причине, что и
alerting — `config/` ваш. Перенесите его в SSoT, если предпочитаете централизацию.

### Handoff: lane `vps` → lane `core-pipeline`

`deploy/vps/` завершён и проверен ([tasks/vps-deploy-tooling.md](tasks/vps-deploy-tooling.md)),
но реальный деплой всё ещё останавливается на preflight из-за одного отсутствующего артефакта в
**вашем** lane:

- **`integrations/prefect/deploy.py` не существует** → `just prefect-deploy` и шагу 5 `deploy.sh`
  нечего вызывать. (`deploy/docker-compose.yml`, второе предусловие, приземлился
  с obs/compose-lane 2026-07-17.)

`deploy.sh` делает preflight и отказывается стартовать вместо полу-деплоя, так что это чистый
блок, а не мина. Больше ничто в `deploy/vps/` вас не требует: настройки читаются прямо из
`config/config.yml → deploy.vps.*` через `yq`, поэтому `config/.env-render.py` **не** потребовал изменений.

**Решение, которое несёт `deploy.py` (это не просто отсутствующий файл — помечено из vps-lane, 2026-07-18):**
написать его — значит выбрать **модель запуска** Prefect, а репозиторий сейчас её недоопределяет —
стоит решить до написания, потому что выбор дотягивается и до compose-lane.

- Шаг 5 `deploy.sh` — **one-shot** (`uv run python integrations/prefect/deploy.py`), поэтому
  `deploy.py` должен **зарегистрировать deployment и вернуться** — `flow.serve()` блокируется
  навсегда и повесил бы шаг деплоя. Регистрировать, а не serve.
- Compose-стек (`deploy/docker-compose.yml`) запускает **Prefect-сервер, но не worker**, а
  `pipelines/flows/main.py` документирует flow как *«runs ephemerally (no server needed)»* —
  эти два факта противоречат друг другу, так что целевой рантайм ещё не зафиксирован. Prefect 3.7.8.
- Два целостных варианта решения:
  - **на основе serve()** (рекомендация vps-lane — самый простой, самодостаточный): `deploy.py`
    создаёт scheduled deployment, а **отдельный** долгоживущий процесс `flow.serve(cron=…)`
    работает как один compose/systemd-сервис. Без work pool, без worker'а. Минимум движущихся
    частей; сервер остаётся UI-only. Соответствует принципу «без лишней инфраструктуры».
  - **worker + work-pool** (больше масштаба, больше частей): `deploy.py` делает `flow.deploy(work_pool_name=…)`
    против сервера, и в compose добавляется **новый сервис `prefect-worker`** (эта половина —
    за compose-lane). Выбирайте это, только если горизонтальное исполнение действительно нужно.
- В любом случае это **~1 файл + 1 compose-сервис**, а не один лишь `deploy.py` — именно процесс
  worker/serve фактически исполняет запуски; `deploy.py` сам по себе регистрирует deployment,
  который никто не подхватит. Подтвердите модель — и тогда файл окажется маленьким.

### Handoff: lane `s3` → lane `core-pipeline`

Объектное хранилище отгружено и проверено ([tasks/s3-object-storage.md](tasks/s3-object-storage.md)):
`src/ogip/storage.py` резолвит бэкенд → URL бакета + креды, `make storage-up` запускает MinIO,
а round-trip-тест по-настоящему доказывает dlt → `s3://` → DuckDB-over-`httpfs`. Но **все точки
вызова — в вашем lane**, поэтому `local` пока остаётся единственным бэкендом, на котором пайплайн
реально работает. Ничто ниже не меняет текущее поведение — `local` остаётся дефолтом, пока вы это не приземлите.

1. **`ingestion/base/base_source.py:48`** хардкодит локальную ФС →
   `destination=dlt_filesystem_destination(data_dir)` (из `ogip.storage`). `run()` тогда возвращает
   **URL** датасета (`str`, а не `Path`); его единственный вызывающий (`pipelines/flows/main.py:41`) уже
   делает `str(out)`, поэтому flow и его asset key не затронуты.
2. **`spec/sql/raw/*.sql` + компилятор спецификации** — ⚠️ **настоящий блокер.** Слой 0 хардкодит
   `read_parquet('.run/data/raw/rawg__games/*.parquet')`, поэтому SQLMesh продолжает читать локальную ФС
   независимо от того, что dlt пишет в `s3://`. Корень озера должен **инжектироваться компилятором**
   (D0/D5), а не быть литералом; `ogip.storage.raw_bucket_url()` возвращает ровно
   нужный ему префикс.
3. **`transform/sqlmesh/config.yaml`** — конфиг, а не код: `DuckDBConnectionConfig` в SQLMesh
   поддерживает и `extensions: [httpfs]`, и `secrets:`, интерполируемые из слотов `OGIP_S3_*`.
   SQLMesh открывает собственное соединение, поэтому наш `configure_duckdb_s3()` до него не дотягивается.
4. **`config/.env-render.py`** — добавить `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` плюс
   соответствующие dev-дефолты `OGIP_S3_*` в `DEMO_DEFAULTS` (существующий паттерн `OGIP_PG_PASSWORD`),
   чтобы `make storage-up` + `backend: minio` работали с голого checkout'а без ручного заполнения слотов.

`src/ogip/warehouse.py` не требует **ничего**: `export_table` читает собранный warehouse, а не `s3://`.

## Известные битые ссылки

- `just prefect-deploy` / `prefect-run` → `integrations/prefect/{deploy,trigger}.py` — **отсутствуют**
  (lane core-pipeline; `integrations/` ещё не существует). `deploy/vps/smoke.sh` вызывает `trigger.py`.
- ~~`just tasks-sync` → `integrations/github/tasks_sync.py`~~ — **исправлено** 2026-07-17: переписан как
  `src/scripts/tasks_sync.py` (покрыт pyright, в отличие от `integrations/`). Трекер работает:
  [issues #1–#3](https://github.com/dataengy/ogip/issues).

## Сделано

- Создан путь проекта: `~/gi/@dataengy/OGIP`.
- Написан мастер-план создания: [PLAN.md](PLAN.md) (целевой дизайн + 11 фаз + карта переноса).
- Развёрнут хаб `.ai/`: AGENTS · CLAUDE · README · STATUS · PLAN · **TODO** · `tasks/`.
- Развёрнут `docs/`: README · CHANGELOG · ROADMAP; **adr/** (индекс + шаблон + 13 ADR) ·
  **architecture/** (README + обзор) · **runbooks/** (README + шаблон + 4 ранбука).
- `.tmp/` (README + Justfile) для временных скриптов/файлов.

## Зафиксированные решения

| # | Решение |
|---|---|
| D0 | `spec/sql` в **формате Bruin asset**; прочие сущности спецификации в Bruin, где возможно; контракты в **ODCS**. Открытая сериализация авторинга, а не prod-зависимость. |
| D1 | Профили dbt/SQLMesh/Bruin + оркестрации — **запускаемые** демо (в `experimental/`). |
| D2 | Хранилище: **локальная ФС по умолчанию** + **Cloudflare R2** (основное облако) + профили **MinIO** + **S3**. |
| D3 | Prefect — **оба варианта**: ephemeral (по умолчанию) + профиль server-in-compose. |
| D4 | Быстрый срез: Фазы 0–6 на **Steam + RAWG** → демо end-to-end. |
| D5 | **Движок трансформаций по умолчанию = SQLMesh** (из спецификации, на DuckDB, оркестрируется Prefect); plain-SQL/dbt/Bruin = сравнения; нужен компилятор спецификации. |
| D6 | Добавить **слой FS (Feature Store)** `fs_*` (SQL-as-FS → parquet) + анализ целесообразности специализированного FS-инструмента. |
| D7 | **JupyterLab** + демо-ноутбуки `notebooks/` (основной DS-интерфейс). |
| D8 | **Evidence** — опциональное исследование визуализатора для DA/DS/MLE. |
| D9 | Подключён полный стек: типизированный Python · uv · Prefect 3 · **PostgreSQL** (landing + platform_meta + Prefect) · **Cloudflare R2** · **Parquet/PyArrow** · DuckDB · **ручной деплой на VPS** (DevOps отдельно) · GitHub Actions (typecheck + тесты). |
| D10 | **Секреты = минимально и максимально легко**: gitignored **`.env`** (слоты из SSoT) локально+VPS + **секреты GitHub Actions** в CI. Без vault/GPG по умолчанию; Bitwarden CLI и git-secret — opt-in (задокументировано). |
| D11 | **Инжестия: dlt по умолчанию** (через `BaseSource`); **ingestr опционально (CDC)**; scraped/parsed-данные попадают в **PostgreSQL `landing`**, затем dlt/ingestr загружают их в сырой Parquet. |
| D12 | **Трекинг задач = GitHub Issues/Projects**: `.ai/tasks/` ↔ Issues/доска через `just tasks-sync`; `.ai/TODO.md` = короткий упорядоченный чек-лист со ссылками на задачи. |
| D13 | **Добавить слой AM (Activity Model)** — Activity Schema `am_<entity>_stream`; дополняет STAR Кимбалла над CORE (демонстрируются 4 техники моделирования). |
| D14 | **Поставка = сначала walking skeleton** — минимальный полный срез (1 источник→raw→spec→SQLMesh→ML parquet→ноутбук+Evidence, Prefect+dlt), затем тиражирование на тулсеты; **запуск в Docker + Prefect после каждого** (`integrations/prefect/`). |
| D15 | **Commit + push после каждого успешного прогона** (зелёный gate / зелёный пайплайн). |
| D16 | **Pre-commit через prek** (быстрый) — линт ВСЕГО (Python·SQL·Bash·YAML) + smoke-тесты на commit, data-тесты на pre-push, gitleaks. |
| D17 | **Уровни тестов** smoke / unit / integration / **e2e = запустить Prefect-джобу + проверить результаты**. |
| D18 | **Root-lean**: конфиги→`config/`, тесты→`src/tests/`, скрипты→`src/scripts/`, CI→`.ci/`; guard `structure-validate`. |
| D19 | **Симлинки `.ai/`** для планов/памяти/скиллов (memory·skills в gitignore; specs·scripts отслеживаются). |
| D20 | _(отложено)_ позже — upsert кода + scaffold **стандартов в `~/.ai/skills/.settings/code_specs/`**. |
| + | Полные альтернативные setup'ы **Prefect+Bruin** и **Prefect+Dagster-over-dlt/dbt**; **CDC через ingestr** из landing Postgres (опционально). |

Допущения: свежий `git init` · OGAP остаётся соседним репозиторием · GitHub Actions — основной CI · пакет `ogip`.

Открытая проектная заметка: D0 (авторинг в Bruin) + D5 (запуск на SQLMesh) подразумевает шаг
компиляции спецификации — помечено для пользователя; альтернатива — авторинг нативно в SQLMesh.

## Следующие шаги

Финализационный DAG (2026-07-30) — единственный источник:
[docs/superpowers/plans/2026-07-30-finalization-land-everything.md](../docs/superpowers/plans/2026-07-30-finalization-land-everything.md):

1. **B** — три зелёные run-команды (`run-dbt` · `run-bruin` · `run-dagster-dbt` — последняя
   уже существует как `prefect-over-dagster`, [tasks/run-dagster-dbt-profile.md](tasks/run-dagster-dbt-profile.md))
   + громкая заглушка DQ (loud-stub).
2. **C** — re-root T4–T9 ([#40](https://github.com/dataengy/ogip/issues/40)) → PR reroot→dev.
3. **D** — приземлить dagster #34 + odos #37, удалить выведенные из работы ветки, DQ-минимум,
   развёртка TBD ([реестр](../docs/techdebt/finalization-tbd.md)), обновление документации, dev→main #10.
4. Прежние P1 (устойчивый скрейпинг [#18](https://github.com/dataengy/ogip/issues/18),
   R2+VPS [#17](https://github.com/dataengy/ogip/issues/17)) свёрнуты в TBD-реестр /
   объём V2 — отложены громко, а не выброшены.
