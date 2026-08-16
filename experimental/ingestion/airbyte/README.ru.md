<!-- ru-translation-of: experimental/ingestion/airbyte/README.md sha:c6d8b9a4ea86 -->
<!-- Автоперевод. Источник — experimental/ingestion/airbyte/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# Airbyte + Terraform — lane для оценки

> **Экспериментально. Вне `make`-пути.** Этот lane **оценивает** Airbyte; это не
> продакшен-инжест. Продуктовый инжест идёт через **dlt**. Ничто отсюда не подключено к `make run`.

- **Трекер:** [#41](https://github.com/dataengy/ogip/issues/41) · файл задачи `.ai/tasks/airbyte-evaluation-lane.md`
- **SSoT дизайна:** [`docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md`](../../../docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md)
- **План:** [`docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.md`](../../../docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.md)
- **Техдолг:** [`docs/techdebt/airbyte-lane.md`](../../../docs/techdebt/airbyte-lane.md)

## Зачем этот lane существует

Аудит 591 источника живого OSS-реестра нашёл **ноль** коннекторов Airbyte для реальных
источников домена рынка игр (Steam, MobyGames, Gamalytic, SteamDB, HLTB, IGDB, itch, Epic, GOG,
PSN, Xbox, Nintendo, Kickstarter). Поэтому lane оценивает инструмент на **единственном** кейсе,
который его действительно заслуживает — `github_repos` через `airbyte/source-github`,
единственный коннектор, который одновременно *сертифицирован*, **и** является настоящим кодом,
**и** работает с публичными данными (39 из 59 сертифицированных источников — YAML-манифесты
без кода). Активность экосистемы движков (Godot/Bevy/O3DE + длинный хвост моддинга) — реальный
вход для моделей scope/budget.

Полное сравнение лоб в лоб: [`docs/comparisons/github_repos-ingestion-dlt-vs-airbyte-vs-custom.md`](../../../docs/comparisons/github_repos-ingestion-dlt-vs-airbyte-vs-custom.md).

## Структура

```
experimental/ingestion/airbyte/
  up.sh / down.sh                  abctl local install/uninstall; port from the config SSoT
  credentials.sh                   abctl local credentials → AIRBYTE_CLIENT_ID/SECRET
  connectors/twitch/manifest.yaml  low-code declarative connector for Helix (source-twitch
                                   does not exist in the registry)
  terraform/
    modules/airbyte-connection/    airbyte_source + airbyte_connection + one shared destination
    variant-a-yamldecode/          fileset() + yamldecode() over spec/ — zero generation
    variant-b-codegen-tf/          generated .tf, committed
    variant-c-codegen-tfvars/      generated .tfvars.json + hand-written HCL
```

Между вариантами различается только *способ, которым конфигурация попадает в модуль*;
определения ресурсов общие. Иначе сравнение нечестно, а HCL утраивается.

## Факты, которые кусаются

- Airbyte OSS **удалил docker-compose** (2024-08-23, PR #13544). Оба поддерживаемых пути —
  `abctl` и Helm — заканчиваются Kubernetes. Compose-файла здесь нет намеренно.
- Terraform-провайдер — это **8 универсальных ресурсов**, а не по одному на коннектор. Запинен
  на **1.2.0** (1.3.0 существует только как `-rc1`). `definition_id` разрешается на лету через
  data source `airbyte_connector_configuration` — никогда не хранится в дескрипторе.
- Аутентификация в OSS — **client credentials с TTL токена 15 минут** — никогда не статический
  bearer, который может истечь посреди apply.
- Источники управляются блоками `airbyte:` в `spec/sources/games/*.yaml`, которые являются
  **односторонней проекцией** из SSoT реестра инжеста
  (`~/.ai/skills/.settings/de/ingestion/sources/`). Правьте реестр, а не проекцию.

## Статус

- **Фаза 0** — config SSoT + каркас ✅
- **Фаза 1** — runtime-скрипты написаны ✅; сам **abctl-runtime — NO-GO на этой машине**
  (диск исчерпан посреди установки; посылка «провайдер↔runtime» из-за этого *не проверена*).
  См. [`docs/techdebt/airbyte-lane.md`](../../../docs/techdebt/airbyte-lane.md#phase-1-result).
- **Фаза 2** — общий модуль `airbyte-connection`, схема сверена с провайдером 1.2.0, `validate` зелёный ✅
- **Фаза 3** — вариант A (`terraform/variant-a-yamldecode/`): `validate` зелёный **офлайн**, и
  через `terraform console` доказано, что он находит `github_repos`+`reddit_posts` из спеков,
  исключает twitch (declarative → фаза 5), собирает 6 стримов github и парсит
  `godotengine/godot` из url дескриптора. `plan`/`apply` — тот самый *измеряемый* датапоинт —
  заблокированы отсутствием runtime.
- **Фаза 6** — CI-джоба `airbyte-tf` (`fmt`+`validate`) ✅
- **Фазы 4, 5, 7** — в ожидании (варианты B/C + drift-гейт; декларативный Twitch; измеренный вердикт).

**Вердикта пока нет — намеренно.** Сравнение трёх вариантов (фаза 7) должно опираться на
*измерения* фаз 3–4 — победитель, объявленный здесь заранее, был бы ровно тем false-green,
ради предотвращения которого существует стандарт `deferred_functionality` этого репозитория.
Проводка варианта A доказана; её измеренный прогон и варианты B/C ждут работающего runtime.
