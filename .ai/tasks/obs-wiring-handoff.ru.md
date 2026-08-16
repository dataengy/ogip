<!-- ru-translation-of: .ai/tasks/obs-wiring-handoff.md sha:6b4c9a9c40e2 -->
<!-- Автоперевод. Источник — .ai/tasks/obs-wiring-handoff.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [obs-wiring-handoff.md](obs-wiring-handoff.md)

# Задача — обвязка obs, handoff (lane obs → core-pipeline)

**Статус:** ✅ сделано — обращённая к пайплайну половина отгруженного обс-стека, которая жила
в lane core-pipeline (`config/`, `pipelines/`), теперь подключена.

## Что lane obs требовал от нас (handoff из STATUS)

1. **Флоу не писал лог-файл** → Alloy тейлил пустой каталог, панели Loki оставались пустыми.
2. **Порты obs так и не доходили до `.env`** → обс-compose откатывался на литералы, дублирующие SSoT.

## Сделано

- `pipelines/flows/main.py` — ежедневный флоу теперь вызывает
  `setup_logging(json_logs=settings.platform.log_json, log_file=settings.platform.log_file)`
  вместо голого `setup_logging()`, так что он пишет структурированный лог-файл (`.run/logs/ogip.log`),
  который тейлится по цепочке Alloy → Loki.
- `config/config.yml` — `platform.log_json: true`, так что файл в JSON и Loki получает распарсенные метки.
- `config/.env-render.py` — `_derived()` теперь маппит `VICTORIAMETRICS_PORT`, `LOKI_PORT`,
  `GRAFANA_PORT` из SSoT `services` в `.env` (их читает обс-compose).

## Проверено

- `make check` зелёный (46 тестов). e2e зелёный + стабильный — флоу пишет `.run/logs/ogip.log`
  (подтверждены 20 JSON-строк). `make render-env` выдаёт три obs-порта + `OGIP_LOG_JSON=true`.

## Вне объёма (по-прежнему lane obs / позже)

- Экспорт OTLP-метрик (`localhost:4318`, префикс `ogip_`) — панель дашборда ждёт; это follow-up
  по инструментированию пайплайна.
- Хук алертинга на отказ уже подключён (`on_failure=[notify_flow_failure]` — его приземлил
  lane alerting).
