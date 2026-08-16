<!-- ru-translation-of: docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.md sha:352f86a2307a -->
<!-- Автоперевод. Источник — docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [2026-07-24-airbyte-lane-implementation.md](2026-07-24-airbyte-lane-implementation.md)

# Оценочная линия Airbyte — план реализации

- **Date:** 2026-07-24 · **Refs:** OGIP#18, OGIP#19
- **Design SSoT:** `docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md`
- **Techdebt tracker:** `docs/techdebt/airbyte-lane.md`
- **Anchor source:** `github_repos` (`airbyte/source-github` 2.1.37 — certified, Python CDK, GA)
- **Isolation:** worktree `OGIP.worktrees/airbyte` на `lane/airbyte` + блокировка `obj--airbyte`
  (существующее соглашение репозитория; НЕ переключение ветки на общем checkout)

## Purpose (не потеряйте эту рамку)

Эта линия **оценивает** Airbyte на его единственном лучшем случае; это не production-ingestion.
Продуктовый ingestion github идёт через dlt (`docs/comparisons/github_repos-ingestion-dlt-vs-airbyte-vs-custom.md`).
Успех = работающее, измеренное сравнение трёх Terraform-драйверов + честный вердикт, с одним
реально синхронизирующим коннектором. Всё остаётся в `experimental/`, вне `make`-пути.

## Preconditions

- Диск ≥ 10Gi свободно (abctl запускает k8s-in-docker). **Сейчас 5Gi — сначала `/clean-disk`.** Жёсткий блок.
- `GITHUB_TOKEN` присутствует (без ключа — 60 req/hr; реальному sync нужно 5,000/hr).
- Docker/colima запущены.

## Phase 0 — Настройка линии и конфигурация

1. `git worktree add OGIP.worktrees/airbyte -b lane/airbyte origin/dev`; захватить блокировку `obj--airbyte`.
2. `config/config.yml`: добавить `services.airbyte_port: 8000` и `postgres.airbyte_schema: airbyte_raw`;
   отобразить обе в `config/.env-render.py`; `make render-env`.
3. Скаффолдинг `experimental/ingestion/airbyte/{terraform/,connectors/,README.md}`.

**Verify:** `make render-env` выдаёт две новые переменные; дерево совпадает со спецификацией §5.

## Phase 1 — Рантайм (abctl) + назначение

1. `up.sh` / `down.sh`, оборачивающие `abctl local install` / `uninstall` (порт из SSoT).
2. `credentials.sh` → `abctl local credentials` → записать `AIRBYTE_CLIENT_ID/SECRET` в `.env`.
3. Создать схему `airbyte_raw` в общем Postgres (идемпотентный DDL).
4. Passthrough в корневом `Justfile`: `airbyte-up`, `airbyte-down`.

**Verify:** `curl localhost:8000/api/public/v1/health` OK; токен client-credentials выпускается;
ручной UI source→dest→connection для github синхронизирует один stream в `airbyte_raw`. **Gate: STOP** —
если ручной sync падает, предположение compose-vs-abctl неверно; отчитайтесь, не заглаживайте.

## Phase 2 — Общий модуль Terraform

1. `terraform/modules/airbyte-connection/`: `airbyte_source` (generic, `definition_id` через
   data source `airbyte_connector_configuration` — никогда не хранится) + один общий `airbyte_destination`
   (postgres → `airbyte_raw`) + `airbyte_connection` (`configurations.streams`, `cursor_field` как
   список, `primary_key` как список-списков).
2. Провайдер закреплён `airbytehq/airbyte 1.2.0`; auth = client credentials; state = локальный файл в `.run/`.

**Verify:** `terraform init` + `validate` зелёные в одноразовом root, вызывающем модуль один раз для github.

## Phase 3 — Вариант A (yamldecode) — ожидаемый победитель

1. `variant-a-yamldecode/`: `fileset()`+`yamldecode()` по `spec/sources/games/*.yaml`, фильтр к
   записям с блоком `airbyte:`, `for_each` по модулю.
2. Root-passthrough `airbyte-tf-plan` / `airbyte-apply` (opt-in, credential-gated).

**Verify:** `plan` показывает ровно 3 airbyte-источника; `apply` их создаёт; github-connection запускает
инкрементальный sync; `stargazers`/`releases` приземляются в `airbyte_raw`. Это измеряемая точка данных.

## Phase 4 — Варианты B и C (для сравнения)

1. Реализовать `airbyte_emit.py render b` (пер-источниковый `.tf`, закоммичен) и `render c`
   (`connections.auto.tfvars.json` + рукописный HCL). Убирает render-заглушку (строка techdebt).
2. `variant-b-codegen-tf/` + `variant-c-codegen-tfvars/` потребляют отрендеренные артефакты.
3. Проверка дрейфа: пере-рендер, `git diff --exit-code` — привязать к области `airbyte-blocks-check.sh`.

**Verify:** все три варианта `plan` дают *один и тот же* набор ресурсов для github; drift-gate падает на
руками отредактированном сгенерированном файле (negative-tested, согласно verify-gate-actually-covers).

## Phase 5 — Декларативный коннектор Twitch

1. `connectors/twitch/manifest.yaml` — low-code Helix (OAuth2 client-credentials, streams
   `streams`,`games`, `full_refresh`).
2. Зарегистрировать через `airbyte_declarative_source_definition` в модуле.

**Verify:** коннектор регистрируется; снапшот Twitch приземляется. (Reddit остаётся как
community-контрпример — без доп. работы.)

## Phase 6 — Gate'ы и CI

1. `.ci/steps/airbyte-tf.sh`: `terraform fmt -check` + `validate` на всех трёх вариантах (без API).
2. `airbyte-blocks-check.sh` уже гейтит блоки; расширить CI, чтобы гонять `fmt`/`validate`/drift.
   `plan`/`apply` остаются локальными (документированное ограничение, не долг).

**Verify:** CI зелёный на PR, затрагивающем `terraform/`; проходит без учётных данных и достижимого API.

## Phase 7 — Завершение навыка + результат

1. Завершить `/create-skill` шаги 13-15 для `/add-airbyte-sync` (hardlink в `~/.claude/skills`,
   sync targets, INDEX) — теперь, когда `render`/`apply` реальны.
2. Написать `experimental/ingestion/airbyte/README.md`: сравнение трёх вариантов с **измеренным**
   вердиктом (ожидается: Вариант A побеждает — нулевой codegen-дрейф) и честный отрицательный
   результат (github — единственный источник, оправдавший что-либо из этого; observability + вес
   рантайма + «не подключаем managed-коннекторы» со стороны клиента держат его вне prod).

**Verify:** README излагает вердикт, подкреплённый измерениями Phase 3-4, а не прогнозом.

## Risks / stop conditions

- Gate Phase 1 — реальный go/no-go: если abctl + провайдер 1.2.0 не договариваются, вся рантайм-
  предпосылка рушится — вынесите это наружу, не форсируйте compose-v0.63.
- Диск: abctl тяжёл; перепроверьте свободное место перед Phase 1.
- Дисциплина линии: пуш через одноразовый worktree, если общий checkout сталкивается
  ([[ogip-shared-checkout-worktree-push]]).
