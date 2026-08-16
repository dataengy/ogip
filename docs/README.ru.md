<!-- ru-translation-of: docs/README.md sha:07d29533704b -->
<!-- Автоперевод. Источник — docs/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# OGIP — Документация

**OGIP · Open Games Intelligence Platform** — платформа рыночной аналитики (Market
Intelligence Platform), превращающая публичные данные игрового рынка в **готовые к ML
датасеты в формате Parquet** для Data Scientist'ов, ML-инженеров и аналитиков.

| Документ | Что это |
|---|---|
| [architecture/](architecture/) | Проектирование системы: [обзор](architecture/overview.md) + подтемы по отдельным документам |
| [adr/](adr/) | Записи об архитектурных решениях (Architecture Decision Records, ADR-0001…, с индексом) |
| [runbooks/](runbooks/) | Операционные процедуры (локальная разработка, запуск пайплайна, деплой, разбор инцидентов) |
| [ROADMAP.md](ROADMAP.md) | Фазы поставки + текущие приоритеты |
| [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) | Открытые вопросы по требованиям (скрейпинг · объёмы · serving/FS/семантика · SQL+Python) с дефолтами и триггерами решений |
| DATASETS.md | Каталог готовых к ML выходных данных _(Фаза 5)_ |
| [CHANGELOG.md](CHANGELOG.md) | Значимые изменения |
| `comparisons/` | Учебное, изолированное исследование: `dbt-vs-sqlmesh` · `dbt-vs-bruin` · `sqlmesh-vs-bruin` · `plain-sql-vs-frameworks` · `iceberg-vs-ducklake` · `dlt-vs-ingestr` (включая CDC) · `feature-store-tools` · `visualizers-evidence` · `secrets-management` · `modeling-techniques` _(Фаза 9)_ |

Основной план создания находится в [.ai/PLAN.md](../.ai/PLAN.md); правила для агентов — в
[.ai/AGENTS.md](../.ai/AGENTS.md).
