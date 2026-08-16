<!-- ru-translation-of: src/ogip/README.md sha:6c4b04ee09ab -->
<!-- Автоперевод. Источник — src/ogip/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# `src/ogip/` — типизированное ядро на Python

Импортируемый пакет (`ogip`). Полностью типизирован, Pyright strict.

| Модуль | Назначение |
|---|---|
| `config.py` | Типизированные настройки из `config/config.yml` (SSoT) + переопределения/секреты из `.env`. |
| `logger.py` | Структурированное логирование на loguru (человекочитаемый + JSON-приёмники). |
| `warehouse.py` | Сессия/хелперы DuckDB _(M0)_. |
| `spec_compile/` | Спека (Bruin) → проекты движков (SQLMesh по умолчанию) _(Phase 3)_. |
| `metrics.py` · `notify.py` | Отправка метрик + абстракция алертов `Notifier` _(Phase 7)_. |

Бизнес-логика для flow живёт здесь; `pipelines/` (Prefect) и `transform/` (SQLMesh) обращаются сюда.
