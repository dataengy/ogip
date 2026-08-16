<!-- ru-translation-of: docs/adr/ADR-0012-github-ci-manual-vps-deploy.md sha:a7a530669aff -->
<!-- Автоперевод. Источник — docs/adr/ADR-0012-github-ci-manual-vps-deploy.md. Правьте источник, затем /translate-md-docs-to-russian. -->

> 🇬🇧 English original: [ADR-0012-github-ci-manual-vps-deploy.md](ADR-0012-github-ci-manual-vps-deploy.md)

# ADR-0012 — GitHub Actions CI + ручной VPS-деплой (DevOps отдельно)

- **Статус:** Принято
- **Дата:** 2026-07-17
- **Связано с:** D9 · `deploy/vps/` · `docs/runbooks/deploy-vps.md`

## Контекст

Проекту нужен гейт на каждое изменение и история развёртывания, но инфраструктура/DevOps
обрабатывается отдельно и вне области действия этого репозитория.

## Решение

**CI = GitHub Actions**: проверка типов (Pyright strict) + набор тестов (pytest) + pre-commit, поверх
общей библиотеки `.ci/steps/`. **Развёртывание = вручную на VPS** через `deploy/vps/` (uv sync, рендер
env, секреты, prefect deploy, compose up), задокументировано как ранбук. Без Kubernetes/Terraform.

## Последствия

- Побайтово стабильная логика CI; warehouse-in-CI дёшев на DuckDB.
- Деплой ручной и управляется ранбуком; автоматизация явно вне области (DevOps отдельно).

## Рассмотренные альтернативы

- **GitLab CI dual-frontend** (OGAP) — оставлен опциональным; GitHub Actions — единственный обязательный CI.
- **k8s/Terraform** — избыточный охват; DevOps владеет инфраструктурой отдельно.
