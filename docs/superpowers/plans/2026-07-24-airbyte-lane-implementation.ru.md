<!-- ru-translation-of: docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.md sha:dbb7d208dddd -->
<!-- Автоперевод. Источник — docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [2026-07-24-airbyte-lane-implementation.md](2026-07-24-airbyte-lane-implementation.md)

# Lane оценки Airbyte — план реализации

- **Дата:** 2026-07-24 · **Refs:** OGIP#41 · файл задачи `.ai/tasks/airbyte-evaluation-lane.md`
  - (Ранние черновики ссылались на #18/#19 — это ошибка: там задачи про resilient-scraping и
    sources-backlog. Трекер этого lane — **#41**.)
- **SSoT дизайна:** `docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md`
- **Трекер техдолга:** `docs/techdebt/airbyte-lane.md`
- **Якорный источник:** `github_repos` (`airbyte/source-github` 2.1.37 — certified, Python CDK, GA)
- **Изоляция:** worktree `OGIP.worktrees/airbyte` на `lane/airbyte` + лок `obj--airbyte`
  (существующая конвенция репозитория; НЕ переключение ветки в общем чекауте)

## Цель (не терять этот фрейминг)

Этот lane **оценивает** Airbyte на его единственном лучшем кейсе; это не продакшн-инжест. Продуктовый
инжест github идёт через dlt (`docs/comparisons/github_repos-ingestion-dlt-vs-airbyte-vs-custom.md`).
Успех = работающее, измеренное сравнение трёх Terraform-драйверов + честный вердикт, при этом один
коннектор реально синхронизируется. Всё остаётся в `experimental/`, вне пути `make`.

## Предусловия

- Диск ≥ 10Gi свободно (abctl запускает k8s-in-docker). **Сейчас 5Gi — сначала `/clean-disk`.** Жёсткий блокер.
- Есть `GITHUB_TOKEN` (без ключа — 60 req/hr; для реального sync нужно 5,000/hr).
- Docker/colima запущены.

## Фаза 0 — Настройка lane и конфигурации

1. `git worktree add OGIP.worktrees/airbyte -b lane/airbyte origin/dev`; занять лок `obj--airbyte`.
2. `config/config.yml`: добавить `services.airbyte_port: 8000` и `postgres.airbyte_schema: airbyte_raw`;
   замапить оба в `config/.env-render.py`; `make render-env`.
3. Заскаффолдить `experimental/ingestion/airbyte/{terraform/,connectors/,README.md}`.

**Проверка:** `make render-env` выдаёт две новые переменные; дерево соответствует спеке §5.

## Фаза 1 — Рантайм (abctl) + destination

1. `up.sh` / `down.sh`, оборачивающие `abctl local install` / `uninstall` (порт из SSoT).
2. `credentials.sh` → `abctl local credentials` → записать `AIRBYTE_CLIENT_ID/SECRET` в `.env`.
3. Создать схему `airbyte_raw` в общем Postgres (идемпотентный DDL).
4. Passthrough в корневом `Justfile`: `airbyte-up`, `airbyte-down`.

**Проверка:** `curl localhost:8000/api/public/v1/health` OK; токен по client-credentials выпускается;
вручную собранная в UI связка source→dest→connection для github синхронизирует один stream в
`airbyte_raw`. **Гейт: STOP** — если ручной sync падает, предположение compose-vs-abctl неверно;
доложить, а не замазывать.

## Фаза 2 — Общий Terraform-модуль

1. `terraform/modules/airbyte-connection/`: `airbyte_source` (обобщённый, `definition_id` через
   data source `airbyte_connector_configuration` — никогда не хранится) + один общий `airbyte_destination`
   (postgres → `airbyte_raw`) + `airbyte_connection` (`configurations.streams`, `cursor_field` как
   список, `primary_key` как список списков).
2. Провайдер запинен на `airbytehq/airbyte 1.2.0`; auth = client credentials; state = локальный файл в `.run/`.

**Проверка:** `terraform init` + `validate` зелёные в одноразовом корне, вызывающем модуль один раз для github.

## Фаза 3 — Вариант A (yamldecode) — ожидаемый победитель

1. `variant-a-yamldecode/`: `fileset()`+`yamldecode()` по `spec/sources/games/*.yaml`, фильтр по
   записям с блоком `airbyte:`, `for_each` по модулю.
2. Корневые passthrough `airbyte-tf-plan` / `airbyte-apply` (opt-in, за гейтом креденшалов).

**Проверка:** `plan` показывает ровно 3 airbyte-источника; `apply` их создаёт; connection для github
выполняет инкрементальный sync; `stargazers`/`releases` приземляются в `airbyte_raw`. Это и есть
измеренная точка данных.

## Фаза 4 — Варианты B и C (для сравнения)

1. Реализовать `airbyte_emit.py render b` (по-источниковые `.tf`, коммитятся) и `render c`
   (`connections.auto.tfvars.json` + рукописный HCL). Убирает render-заглушку (строка техдолга).
2. `variant-b-codegen-tf/` + `variant-c-codegen-tfvars/` потребляют срендеренные артефакты.
3. Проверка дрифта: перерендер, `git diff --exit-code` — вписать в зону охвата `airbyte-blocks-check.sh`.

**Проверка:** все три варианта дают `plan` с *одним и тем же* набором ресурсов для github; дрифт-гейт
падает на вручную отредактированном сгенерированном файле (протестировано негативно, по
verify-gate-actually-covers).

## Фаза 5 — Декларативный коннектор Twitch

1. `connectors/twitch/manifest.yaml` — low-code Helix (OAuth2 client-credentials, стримы
   `streams`,`games`, `full_refresh`).
2. Зарегистрировать через `airbyte_declarative_source_definition` в модуле.

**Проверка:** коннектор регистрируется; снапшот Twitch приземляется. (Reddit остаётся как
community-контрпример — без дополнительной работы.)

## Фаза 6 — Гейты и CI

1. `.ci/steps/airbyte-tf.sh`: `terraform fmt -check` + `validate` на всех трёх вариантах (без API).
2. `airbyte-blocks-check.sh` уже гейтит блоки; расширить CI до запуска `fmt`/`validate`/дрифта.
   `plan`/`apply` остаются только локальными (задокументированное ограничение, а не долг).

**Проверка:** CI зелёный на PR, затрагивающем `terraform/`; проходит без креденшалов и без доступного API.

## Фаза 7 — Завершение скилла + деливерабл

1. Доделать шаги 13-15 `/create-skill` для `/add-airbyte-sync` (хардлинк в `~/.claude/skills`,
   sync-таргеты, INDEX) — теперь, когда `render`/`apply` реальны.
2. Написать `experimental/ingestion/airbyte/README.md`: сравнение трёх вариантов с
   **измеренным** вердиктом (ожидается: побеждает Вариант A — нулевой дрифт кодгена) и честным
   отрицательным результатом (github — единственный источник, оправдавший всё это; наблюдаемость +
   вес рантайма + клиентское «managed-коннекторы не подключаем» держат его вне прода).

**Проверка:** README формулирует вердикт, подкреплённый измерениями Фаз 3-4, а не предсказанием.

## Риски / стоп-условия

- Гейт Фазы 1 — настоящий go/no-go: если abctl и провайдер 1.2.0 не договорятся, вся посылка
  рантайма рушится — вынести это наружу, не форсить compose-v0.63.
- Диск: abctl тяжёлый; перепроверить свободное место перед Фазой 1.
- Дисциплина lane: пушить через одноразовый worktree, если общий чекаут конфликтует
  ([[ogip-shared-checkout-worktree-push]]).
