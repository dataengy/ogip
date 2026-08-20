<!-- GENERATED from docs/TRANSLATIONS.ru.yml — не редактируйте вручную; правьте .yml / перезапустите /translate-md-docs-to-russian -->

# OGIP — Реестр переводов (RU)

Единый указатель русских переводов документации репозитория. **Источник истины —
`docs/TRANSLATIONS.ru.yml`**; этот `.md` — сгенерированное человекочитаемое представление.
Оба файла **не отслеживаются git** (по умолчанию, как и все `*.ru.md`).

## Как это работает

- На каждый `foo.md` создаётся `foo.ru.md` с маркером происхождения в первой строке:
  `<!-- ru-translation-of: foo.md sha:<первые 12 символов git hash-object> -->`.
- Скилл `/translate-md-docs-to-russian` перечисляет исходники, у которых перевод
  **отсутствует** или **устарел** (записанный `sha` ≠ текущему `git hash-object`), и
  переводит только их. Код, ссылки-цели, идентификаторы и якоря сохраняются дословно.
- Глоссарии (`.ai/AI-glossary.ru.md` и др.) — это **компаньоны без `.md`-исходника**;
  их ведут вручную (скилл `/update-terms-glossaries`), автоперевод их **не трогает**.

## Когда и как обновлять

| Событие | Что делать |
|---|---|
| Изменён исходный `*.md` | `/translate-md-docs-to-russian` → перевод помечается `stale` по несовпадению `sha` и переводится заново |
| Добавлен новый `*.md` | тот же запуск подхватит его как `missing` |
| Нужен подмножественный прогон | `/translate-md-docs-to-russian --scope=core` (корень + `docs/`) |
| Опубликовать переводы в git | `/translate-md-docs-to-russian --track` (форс-добавит `*.ru.md`) |
| Обновить этот реестр | шаг manifest скилла: пересобрать `.yml`, затем отрендерить `.md` из него |
| Термины/глоссарий | `/update-terms-glossaries` — он владеет RU-глоссарием |

> Порядок на следующем прогоне: **1)** перевести устаревшие/новые → **2)** пересобрать
> `TRANSLATIONS.ru.yml` → **3)** отрендерить `TRANSLATIONS.ru.md`. Реестр всегда следует
> за фактическими `*.ru.md`, а не наоборот.

## Переводы

| Источник | Перевод | Состояние |
|---|---|---|
| `.ai/AGENTS.md` | `.ai/AGENTS.ru.md` | ✅ up-to-date |
| `.ai/CLAUDE.md` | `.ai/CLAUDE.ru.md` | ✅ up-to-date |
| `.ai/FIXME.md` | `.ai/FIXME.ru.md` | ✅ up-to-date |
| `.ai/PLAN.md` | `.ai/PLAN.ru.md` | ✅ up-to-date |
| `.ai/README.md` | `.ai/README.ru.md` | ✅ up-to-date |
| `.ai/SKILLS.md` | `.ai/SKILLS.ru.md` | ✅ up-to-date |
| `.ai/STATUS.md` | `.ai/STATUS.ru.md` | ✅ up-to-date |
| `.ai/TODO.md` | `.ai/TODO.ru.md` | ✅ up-to-date |
| `.ai/WiP/HANDOFF-2026-08-16-ru-docs-branch.md` | `.ai/WiP/HANDOFF-2026-08-16-ru-docs-branch.ru.md` | ✅ up-to-date |
| `.ai/WiP/HANDOFF-2026-08-20-cloud-devops-readiness.md` | `.ai/WiP/HANDOFF-2026-08-20-cloud-devops-readiness.ru.md` | ✅ up-to-date |
| `.ai/tasks/README.md` | `.ai/tasks/README.ru.md` | ✅ up-to-date |
| `.ai/tasks/agentic-monitoring.md` | `.ai/tasks/agentic-monitoring.ru.md` | ✅ up-to-date |
| `.ai/tasks/airbyte-evaluation-lane.md` | `.ai/tasks/airbyte-evaluation-lane.ru.md` | ✅ up-to-date |
| `.ai/tasks/alerting.md` | `.ai/tasks/alerting.ru.md` | ✅ up-to-date |
| `.ai/tasks/cloud-devops-readiness.md` | `.ai/tasks/cloud-devops-readiness.ru.md` | ✅ up-to-date |
| `.ai/tasks/dagster-setup.md` | `.ai/tasks/dagster-setup.ru.md` | ✅ up-to-date |
| `.ai/tasks/dbt-packages.md` | `.ai/tasks/dbt-packages.ru.md` | ✅ up-to-date |
| `.ai/tasks/finalization.md` | `.ai/tasks/finalization.ru.md` | ✅ up-to-date |
| `.ai/tasks/m0-walking-skeleton.md` | `.ai/tasks/m0-walking-skeleton.ru.md` | ✅ up-to-date |
| `.ai/tasks/ml-tasks-and-prefect-per-engine-setups.md` | `.ai/tasks/ml-tasks-and-prefect-per-engine-setups.ru.md` | ✅ up-to-date |
| `.ai/tasks/obs-wiring-handoff.md` | `.ai/tasks/obs-wiring-handoff.ru.md` | ✅ up-to-date |
| `.ai/tasks/odos-orchestration-spec.md` | `.ai/tasks/odos-orchestration-spec.ru.md` | ✅ up-to-date |
| `.ai/tasks/phase-0-scaffold.md` | `.ai/tasks/phase-0-scaffold.ru.md` | ✅ up-to-date |
| `.ai/tasks/python-task-integration.md` | `.ai/tasks/python-task-integration.ru.md` | ✅ up-to-date |
| `.ai/tasks/r2-vps-finalize.md` | `.ai/tasks/r2-vps-finalize.ru.md` | ✅ up-to-date |
| `.ai/tasks/run-dagster-dbt-profile.md` | `.ai/tasks/run-dagster-dbt-profile.ru.md` | ✅ up-to-date |
| `.ai/tasks/s3-object-storage.md` | `.ai/tasks/s3-object-storage.ru.md` | ✅ up-to-date |
| `.ai/tasks/scraping-resilient.md` | `.ai/tasks/scraping-resilient.ru.md` | ✅ up-to-date |
| `.ai/tasks/session-coordination.md` | `.ai/tasks/session-coordination.ru.md` | ✅ up-to-date |
| `.ai/tasks/sources-backlog.md` | `.ai/tasks/sources-backlog.ru.md` | ✅ up-to-date |
| `.ai/tasks/spec-compact-header.md` | `.ai/tasks/spec-compact-header.ru.md` | ✅ up-to-date |
| `.ai/tasks/spec-macros.md` | `.ai/tasks/spec-macros.ru.md` | ✅ up-to-date |
| `.ai/tasks/spec-semantic-layer.md` | `.ai/tasks/spec-semantic-layer.ru.md` | ✅ up-to-date |
| `.ai/tasks/transform-engine-generators.md` | `.ai/tasks/transform-engine-generators.ru.md` | ✅ up-to-date |
| `.ai/tasks/vps-deploy-tooling.md` | `.ai/tasks/vps-deploy-tooling.ru.md` | ✅ up-to-date |
| `.ci/README.md` | `.ci/README.ru.md` | ✅ up-to-date |
| `.claude/CLAUDE.md` | `.claude/CLAUDE.ru.md` | ✅ up-to-date |
| `.claude/agents/ogip-cloud-devops.md` | `.claude/agents/ogip-cloud-devops.ru.md` | ✅ up-to-date |
| `.claude/agents/ogip-ingestion-engineer.md` | `.claude/agents/ogip-ingestion-engineer.ru.md` | ✅ up-to-date |
| `.claude/agents/ogip-lane-worker.md` | `.claude/agents/ogip-lane-worker.ru.md` | ✅ up-to-date |
| `.claude/agents/ogip-obs-engineer.md` | `.claude/agents/ogip-obs-engineer.ru.md` | ✅ up-to-date |
| `.claude/agents/ogip-workstation-migrator.md` | `.claude/agents/ogip-workstation-migrator.ru.md` | ✅ up-to-date |
| `AGENTS.md` | `AGENTS.ru.md` | ✅ up-to-date |
| `README.md` | `README.ru.md` | ✅ up-to-date |
| `config/README.md` | `config/README.ru.md` | ✅ up-to-date |
| `config/secrets/README.md` | `config/secrets/README.ru.md` | ✅ up-to-date |
| `deploy/README.md` | `deploy/README.ru.md` | ✅ up-to-date |
| `deploy/obs/README.md` | `deploy/obs/README.ru.md` | ✅ up-to-date |
| `deploy/vps/README.md` | `deploy/vps/README.ru.md` | ✅ up-to-date |
| `docs/OPEN-QUESTIONS.md` | `docs/OPEN-QUESTIONS.ru.md` | ✅ up-to-date |
| `docs/README.md` | `docs/README.ru.md` | ✅ up-to-date |
| `docs/ROADMAP.md` | `docs/ROADMAP.ru.md` | ✅ up-to-date |
| `docs/RU-DOCS-BRANCH.md` | `docs/RU-DOCS-BRANCH.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0001-edw-layering-no-medallion.md` | `docs/adr/ADR-0001-edw-layering-no-medallion.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0002-duckdb-analytical-engine.md` | `docs/adr/ADR-0002-duckdb-analytical-engine.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0003-parquet-lake-defer-iceberg-ducklake.md` | `docs/adr/ADR-0003-parquet-lake-defer-iceberg-ducklake.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0004-sqlmesh-default-transform-engine.md` | `docs/adr/ADR-0004-sqlmesh-default-transform-engine.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0005-spec-ssot-bruin-odcs-compiler.md` | `docs/adr/ADR-0005-spec-ssot-bruin-odcs-compiler.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0006-dlt-default-ingestion-postgres-landing.md` | `docs/adr/ADR-0006-dlt-default-ingestion-postgres-landing.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0007-prefect-orchestration.md` | `docs/adr/ADR-0007-prefect-orchestration.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0008-postgresql-roles.md` | `docs/adr/ADR-0008-postgresql-roles.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0009-ml-outputs-feature-store.md` | `docs/adr/ADR-0009-ml-outputs-feature-store.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0010-activity-model-layer.md` | `docs/adr/ADR-0010-activity-model-layer.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0011-minimal-secrets.md` | `docs/adr/ADR-0011-minimal-secrets.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0012-github-ci-manual-vps-deploy.md` | `docs/adr/ADR-0012-github-ci-manual-vps-deploy.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0013-github-issues-projects-tasks.md` | `docs/adr/ADR-0013-github-issues-projects-tasks.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0014-resilient-scraping-concurrency.md` | `docs/adr/ADR-0014-resilient-scraping-concurrency.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0015-dagster-alt-orchestration-dg-components.md` | `docs/adr/ADR-0015-dagster-alt-orchestration-dg-components.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0016-odts-authoring-format-spec-sql.md` | `docs/adr/ADR-0016-odts-authoring-format-spec-sql.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0017-odos-normative-profile.md` | `docs/adr/ADR-0017-odos-normative-profile.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0018-odts-normative-profile.md` | `docs/adr/ADR-0018-odts-normative-profile.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0019-odts-dq-projection-and-seven-prefect-subprojects.md` | `docs/adr/ADR-0019-odts-dq-projection-and-seven-prefect-subprojects.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0020-dbt-bruin-primary-transform-engines.md` | `docs/adr/ADR-0020-dbt-bruin-primary-transform-engines.ru.md` | ✅ up-to-date |
| `docs/adr/ADR-0021-orchestrator-transform-dq-boundary.md` | `docs/adr/ADR-0021-orchestrator-transform-dq-boundary.ru.md` | ✅ up-to-date |
| `docs/adr/README.md` | `docs/adr/README.ru.md` | ✅ up-to-date |
| `docs/adr/_template.md` | `docs/adr/_template.ru.md` | ✅ up-to-date |
| `docs/architecture/README.md` | `docs/architecture/README.ru.md` | ✅ up-to-date |
| `docs/architecture/observability.md` | `docs/architecture/observability.ru.md` | ✅ up-to-date |
| `docs/architecture/overview.md` | `docs/architecture/overview.ru.md` | ✅ up-to-date |
| `docs/architecture/storage.md` | `docs/architecture/storage.ru.md` | ✅ up-to-date |
| `docs/comparisons/dagster-odp-vs-spec-compiler.md` | `docs/comparisons/dagster-odp-vs-spec-compiler.ru.md` | ✅ up-to-date |
| `docs/comparisons/github_repos-ingestion-dlt-vs-airbyte-vs-custom.md` | `docs/comparisons/github_repos-ingestion-dlt-vs-airbyte-vs-custom.ru.md` | ✅ up-to-date |
| `docs/comparisons/ots-vs-odts.md` | `docs/comparisons/ots-vs-odts.ru.md` | ✅ up-to-date |
| `docs/comparisons/scraping-candidates-after-registry-exhausted.md` | `docs/comparisons/scraping-candidates-after-registry-exhausted.ru.md` | ✅ up-to-date |
| `docs/comparisons/secrets-management.md` | `docs/comparisons/secrets-management.ru.md` | ✅ up-to-date |
| `docs/runbooks/README.md` | `docs/runbooks/README.ru.md` | ✅ up-to-date |
| `docs/runbooks/_template.md` | `docs/runbooks/_template.ru.md` | ✅ up-to-date |
| `docs/runbooks/deploy-vps.md` | `docs/runbooks/deploy-vps.ru.md` | ✅ up-to-date |
| `docs/runbooks/local-dev.md` | `docs/runbooks/local-dev.ru.md` | ✅ up-to-date |
| `docs/runbooks/new-workstation.md` | `docs/runbooks/new-workstation.ru.md` | ✅ up-to-date |
| `docs/runbooks/pipeline-failure.md` | `docs/runbooks/pipeline-failure.ru.md` | ✅ up-to-date |
| `docs/runbooks/run-dagster.md` | `docs/runbooks/run-dagster.ru.md` | ✅ up-to-date |
| `docs/runbooks/run-pipeline.md` | `docs/runbooks/run-pipeline.ru.md` | ✅ up-to-date |
| `docs/superpowers/plans/2026-07-20-add-data-source-skill-decomposition.md` | `docs/superpowers/plans/2026-07-20-add-data-source-skill-decomposition.ru.md` | ✅ up-to-date |
| `docs/superpowers/plans/2026-07-20-handoff-prompts.md` | `docs/superpowers/plans/2026-07-20-handoff-prompts.ru.md` | ✅ up-to-date |
| `docs/superpowers/plans/2026-07-20-odos-task-registry.md` | `docs/superpowers/plans/2026-07-20-odos-task-registry.ru.md` | ✅ up-to-date |
| `docs/superpowers/plans/2026-07-20-source-dod-registry-and-domain-docs.md` | `docs/superpowers/plans/2026-07-20-source-dod-registry-and-domain-docs.ru.md` | ✅ up-to-date |
| `docs/superpowers/plans/2026-07-23-transform-expansion-and-six-prefect-subprojects.md` | `docs/superpowers/plans/2026-07-23-transform-expansion-and-six-prefect-subprojects.ru.md` | ✅ up-to-date |
| `docs/superpowers/plans/2026-07-23-wire-scraper-tasks-into-orchestration-layers.md` | `docs/superpowers/plans/2026-07-23-wire-scraper-tasks-into-orchestration-layers.ru.md` | ✅ up-to-date |
| `docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.md` | `docs/superpowers/plans/2026-07-24-airbyte-lane-implementation.ru.md` | ✅ up-to-date |
| `docs/superpowers/plans/2026-07-24-reroot-dbt-bruin-primary-candidates.md` | `docs/superpowers/plans/2026-07-24-reroot-dbt-bruin-primary-candidates.ru.md` | ✅ up-to-date |
| `docs/superpowers/plans/2026-07-30-finalization-land-everything.md` | `docs/superpowers/plans/2026-07-30-finalization-land-everything.ru.md` | ✅ up-to-date |
| `docs/superpowers/specs/2026-07-20-odos-orchestration-spec-design.md` | `docs/superpowers/specs/2026-07-20-odos-orchestration-spec-design.ru.md` | ✅ up-to-date |
| `docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.md` | `docs/superpowers/specs/2026-07-23-airbyte-terraform-lane-design.ru.md` | ✅ up-to-date |
| `docs/techdebt/airbyte-lane.md` | `docs/techdebt/airbyte-lane.ru.md` | ✅ up-to-date |
| `docs/techdebt/finalization-tbd.md` | `docs/techdebt/finalization-tbd.ru.md` | ✅ up-to-date |
| `docs/techdebt/stale-branches.md` | `docs/techdebt/stale-branches.ru.md` | ✅ up-to-date |
| `dq/README.md` | `dq/README.ru.md` | ✅ up-to-date |
| `experimental/ingestion/airbyte/README.md` | `experimental/ingestion/airbyte/README.ru.md` | ✅ up-to-date |
| `experimental/orchestration/dagster_ogip/README.md` | `experimental/orchestration/dagster_ogip/README.ru.md` | ✅ up-to-date |
| `experimental/orchestration/dagster_ogip/cdc/README.md` | `experimental/orchestration/dagster_ogip/cdc/README.ru.md` | ✅ up-to-date |
| `experimental/pipelines/README.md` | `experimental/pipelines/README.ru.md` | ✅ up-to-date |
| `experimental/python_tasks/README.md` | `experimental/python_tasks/README.ru.md` | ✅ up-to-date |
| `ingestion/README.md` | `ingestion/README.ru.md` | ✅ up-to-date |
| `ingestion/samples/README.md` | `ingestion/samples/README.ru.md` | ✅ up-to-date |
| `pipelines/README.md` | `pipelines/README.ru.md` | ✅ up-to-date |
| `spec/ODOS/IMPLEMENTATION.md` | `spec/ODOS/IMPLEMENTATION.ru.md` | ✅ up-to-date |
| `spec/ODOS/README.md` | `spec/ODOS/README.ru.md` | ✅ up-to-date |
| `spec/ODOS/SPEC.md` | `spec/ODOS/SPEC.ru.md` | ✅ up-to-date |
| `spec/ODOS/examples/README.md` | `spec/ODOS/examples/README.ru.md` | ✅ up-to-date |
| `spec/ODTS/GOVERNING-BRIEF.md` | `spec/ODTS/GOVERNING-BRIEF.ru.md` | ✅ up-to-date |
| `spec/ODTS/IMPLEMENTATION.md` | `spec/ODTS/IMPLEMENTATION.ru.md` | ✅ up-to-date |
| `spec/ODTS/README.md` | `spec/ODTS/README.ru.md` | ✅ up-to-date |
| `spec/ODTS/SPEC.md` | `spec/ODTS/SPEC.ru.md` | ✅ up-to-date |
| `spec/ODTS/examples/README.md` | `spec/ODTS/examples/README.ru.md` | ✅ up-to-date |
| `spec/ODTS/proposals/0.2-compact-projection.md` | `spec/ODTS/proposals/0.2-compact-projection.ru.md` | ✅ up-to-date |
| `spec/ODTS/proposals/README.md` | `spec/ODTS/proposals/README.ru.md` | ✅ up-to-date |
| `spec/README.md` | `spec/README.ru.md` | ✅ up-to-date |
| `spec/contracts/README.md` | `spec/contracts/README.ru.md` | ✅ up-to-date |
| `spec/orchestration/README.md` | `spec/orchestration/README.ru.md` | ✅ up-to-date |
| `spec/sources/README.md` | `spec/sources/README.ru.md` | ✅ up-to-date |
| `spec/sql/AGENTS.md` | `spec/sql/AGENTS.ru.md` | ✅ up-to-date |
| `spec/sql/README.md` | `spec/sql/README.ru.md` | ✅ up-to-date |
| `spec/sql/core/README.md` | `spec/sql/core/README.ru.md` | ✅ up-to-date |
| `spec/sql/fs/README.md` | `spec/sql/fs/README.ru.md` | ✅ up-to-date |
| `spec/sql/raw/README.md` | `spec/sql/raw/README.ru.md` | ✅ up-to-date |
| `spec/sql/staging/README.md` | `spec/sql/staging/README.ru.md` | ✅ up-to-date |
| `src/ogip/README.md` | `src/ogip/README.ru.md` | ✅ up-to-date |
| `src/scripts/README.md` | `src/scripts/README.ru.md` | ✅ up-to-date |
| `src/tests/README.md` | `src/tests/README.ru.md` | ✅ up-to-date |
| `transform/README.md` | `transform/README.ru.md` | ✅ up-to-date |
| `transform/bruin/README.md` | `transform/bruin/README.ru.md` | ✅ up-to-date |
| `transform/dbt/README.md` | `transform/dbt/README.ru.md` | ✅ up-to-date |
| `transform/opendbt/README.md` | `transform/opendbt/README.ru.md` | ✅ up-to-date |
| `transform/sqlmesh_dbt/README.md` | `transform/sqlmesh_dbt/README.ru.md` | ✅ up-to-date |

## Глоссарии / компаньоны

| Файл | Компаньон | Примечание |
|---|---|---|
| `.ai/AI-glossary.ru.md` | `.ai/AI-glossary.en.md` | no .md source; hand-maintained (not auto-translated) |
| `.ai/CONTEXT.man.ru.md` | `null` | no .md source; hand-maintained (not auto-translated) |
| `.ai/outreach-drafts.local.ru.md` | `null` | no .md source; hand-maintained (not auto-translated) |
| `docs/TRANSLATIONS.ru.md` | `null` | no .md source; hand-maintained (not auto-translated) |

## Итого

- Переводов: **145**  ·  Глоссариев/компаньонов: **4**  ·  Требуют обновления: **0**
