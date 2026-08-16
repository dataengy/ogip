<!-- ru-translation-of: docs/runbooks/pipeline-failure.md sha:be037ed3014f -->
<!-- Автоперевод. Источник — docs/runbooks/pipeline-failure.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [pipeline-failure.md](pipeline-failure.md)

# Runbook — Разбор сбоя конвейера

- **Trigger:** прогон Prefect flow завершился ошибкой, или DQ-проверка `error` заблокировала конвейер.
- **Owner:** дежурный оператор. **Urgency:** зависит от SLA по свежести.

## Preconditions

- Доступ к логам/UI Prefect и `platform_meta` в Postgres.

## Steps

1. Определите задачу, завершившуюся ошибкой, в прогоне Prefect (UI или `just prefect-logs <run-id>`).
2. Классифицируйте:
   - **Ingestion** (dlt/ingestr, rate-limit, auth) → проверьте водяной знак источника + `platform_meta.ingestion_runs`.
   - **Transform** (SQLMesh) → прочитайте ошибку модели; проверьте свежесть вышестоящих; `just sqlmesh-audit`.
   - **DQ gate** (`error`) → изучите `platform_meta.dq_results`; решите: карантин или исправление.
3. Устраните первопричину; перезапустите flow (идемпотентен — неизменяемый raw + детерминированные трансформации).

## Verify

- Перезапуск `Completed`; DQ зелёный; выходы обновлены.

## Rollback

- Если отгружена плохая сборка: `make warehouse-reset`, затем перезапуск с последней хорошей загрузки raw.

## Escalation

- Отказы хостов/сервисов → DevOps (отдельно). Отказы источников данных → отметьте в прогоне + повтор с backoff.
