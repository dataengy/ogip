<!-- ru-translation-of: deploy/obs/README.md sha:58cbd49bd54b -->
<!-- Автоперевод. Источник — deploy/obs/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# `deploy/obs/` — стек наблюдаемости

VictoriaMetrics + Loki + Alloy + Grafana, связанные для OGIP (фаза 7). Опционален: пайплайн
проходит зелёным и без него. Архитектура, контракты и известные пробелы:
[`docs/architecture/observability.md`](../../docs/architecture/observability.md).

```bash
make obs-up          # start + verify   → Grafana http://localhost:3300
just obs-smoke-log   # prove the log path end-to-end (no pipeline run needed)
make obs-down        # stop (volumes preserved)
```

## Структура

```
deploy/obs/
├── docker-compose.obs.yml          # the stack (standalone — see below)
├── alloy/config.alloy              # tail logs → Loki; OTLP :4317/:4318 → VictoriaMetrics
├── victoriametrics/scrape.yml      # scrape the stack's own health (NOT the pipeline)
└── grafana/
    ├── provisioning/               # datasources + dashboard provider (no click-ops)
    └── dashboards/*.json           # dashboards as code
```

## Почему отдельный compose-файл

`make obs-up` **не** использует `deploy/docker-compose.yml --profile obs`, хотя когда-то
Makefile так делал: этот базовый файл (Postgres, Prefect, MinIO) принадлежит другим рабочим
lane и ещё не существует. Отдельный файл делает этот стек поставляемым сам по себе и свободным
от конфликтов между параллельными сессиями ([`.ai/STATUS.md`](../../.ai/STATUS.md) → lane `obs`).

Когда базовый compose появится, слияние делается заменой сети `ogip-obs` на
`networks: {ogip: {external: true}}` — определения сервисов менять не нужно.

## Конвенции

- **Порты** берутся из `config/config.yml` (SSoT) через отрендеренный `.env`; фоллбэки
  `${VAR:-default}` зеркалируют SSoT, чтобы голый чекаут всё равно поднимался. См. раздел
  «Ports & the SSoT gap» в архитектурном документе.
- **Healthcheck'и везде, кроме Alloy**: VM/Loki/Grafana проверяют себя busybox-`wget`,
  который есть в их образах. `grafana/alloy` вообще не содержит HTTP-клиента (ни wget/curl/nc),
  поэтому healthcheck там указывал бы на отсутствующий бинарник и вечно висел бы unhealthy —
  подвешивая `up --wait`. [`src/scripts/obs-verify.sh`](../../src/scripts/obs-verify.sh)
  покрывает Alloy и проверяет каждый опубликованный порт с хоста.
- **Healthcheck VM использует `127.0.0.1`, а не `localhost`**: VictoriaMetrics слушает только
  IPv4, а busybox-`wget` резолвит `localhost` сначала в `::1` → connection refused.
- **Дашборды — это код**: правки через UI отключены (`allowUiUpdates: false`). Меняйте JSON и
  перезапускайте `make obs-up`.
- **Алертинг — тоже код**: `grafana/provisioning/alerting/` содержит contact points,
  notification policy и правила; **нативный Telegram contact point** Grafana доставляет
  напрямую (без webhook-приёмника). Учётные данные приходят как env
  (`OGIP_TG_BOT_TOKEN`/`OGIP_TG_CHAT_ID` — безопасны пустыми, никогда в YAML). Подводный
  камень: Grafana заново выводит тип значения, подставленного из env при provisioning, поэтому
  числовому `chatid` нужен трюк с завершающим пробелом (см. `contact-points.yml`).
- **Три пайплайна Alloy**: файловые логи → Loki (`job=ogip`, метки level/source/entity);
  OTLP-метрики → VictoriaMetrics; **OTLP-логи → Loki** (`service_name=claude-code`, только
  метка `event_name` — идентификаторы сессий остаются в строке лога; это путь агентной
  телеметрии, эпик #33, включается опционально через `.claude/settings.local.json`).
- **Образы запинены** — обновляйте версии осознанно, никогда через дрейф `:latest`.
