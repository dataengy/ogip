<!-- ru-translation-of: docs/runbooks/README.md sha:daf5d8b3a4d6 -->
<!-- Автоперевод. Источник — docs/runbooks/README.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [README.md](README.md)

# Ранбуки

Операционные процедуры для OGIP. Развёртывание **ручное на VPS**, а **DevOps обрабатывается
отдельно** ([ADR-0012](../adr/ADR-0012-github-ci-manual-vps-deploy.md)), поэтому эти ранбуки —
операционный источник истины. Используйте [`_template.md`](_template.md) для новых ранбуков.

| Ранбук | Когда | Статус |
|---|---|---|
| [local-dev.md](local-dev.md) | Бутстрап + запуск платформы локально | черновик |
| [run-pipeline.md](run-pipeline.md) | Запуск ежедневного пайплайна / `run-profile` в Docker + Prefect | черновик |
| [deploy-vps.md](deploy-vps.md) | Ручной деплой на VPS | черновик |
| [pipeline-failure.md](pipeline-failure.md) | Триаж упавшего потока Prefect / гейта DQ | черновик |
| [run-dagster.md](run-dagster.md) | Запуск альтернативной оркестрации Dagster (dbt + dlt + ingestr CDC) | черновик |
| [new-workstation.md](new-workstation.md) | Бутстрап R&D на новой машине (клон → секреты → гейты) | черновик |
| backfill.md | Backfill / полное обновление источника | _запланировано_ |
| add-source.md | Добавить новый источник ingestion | _запланировано_ |
| rotate-secrets.md | Ротация секрета | _запланировано_ |

Каждый ранбук: **Триггер → Предусловия → Шаги → Проверка → Откат → Эскалация.**
